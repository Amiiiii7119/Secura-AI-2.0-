import io
import re
import warnings
from typing import Any, Dict, List, Optional
from PIL import Image, ExifTags

from app.schemas.evidence import (
    CameraMetadata,
    DeviceMetadataStatus,
    ConsistencyObservation,
    ConsistencySeverity,
    ContainerConsistencyResult,
    GPSMetadataSummary,
    ImageFormat,
    ImageValidationResult,
    MetadataForensicResult,
    MetadataInventory,
    MetadataStatus,
    ThumbnailAnalysisResult,
    ThumbnailStatus,
)
from app.services.thumbnail_analyzer import analyze_embedded_thumbnail


ORIENTATION_DESCRIPTIONS: Dict[int, str] = {
    1: "Top-left (Normal / 0 deg)",
    2: "Top-right (Flipped horizontal)",
    3: "Bottom-right (Rotated 180 deg)",
    4: "Bottom-left (Flipped vertical)",
    5: "Left-top (Transposed / 90 deg CCW + Flip)",
    6: "Right-top (Rotated 90 deg CW)",
    7: "Right-bottom (Transverse / 90 deg CW + Flip)",
    8: "Left-bottom (Rotated 270 deg CW / 90 deg CCW)",
}

EDITING_SOFTWARE_KEYWORDS: List[str] = [
    "photoshop", "gimp", "canva", "lightroom", "paint.net",
    "stable diffusion", "midjourney", "dall-e", "adobe",
    "affinity", "procreate", "snapseed", "vsco", "pixlr"
]


def _safe_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    try:
        s = str(val).strip()
        cleaned = "".join(ch for ch in s if (32 <= ord(ch) <= 126) or (ord(ch) in (9, 10, 13))).strip()
        return cleaned if cleaned else None
    except Exception:
        return None


def _check_container_consistency(
    image: Image.Image,
    validation_result: ImageValidationResult,
    camera_meta: Optional[CameraMetadata],
    thumbnail_result: ThumbnailAnalysisResult,
) -> ContainerConsistencyResult:
    observations: List[ConsistencyObservation] = []

    # 1. Format concordance: detected format vs decoded format
    decoded_format_str = (image.format or "").upper()
    detected_format_str = validation_result.detected_format.value.upper()
    if decoded_format_str and decoded_format_str != detected_format_str:
        observations.append(
            ConsistencyObservation(
                check_name="format_concordance",
                severity=ConsistencySeverity.INCONSISTENCY,
                observed_state=f"Magic byte detected format '{detected_format_str}' differs from decoder format '{decoded_format_str}'",
                benign_explanation="Container encapsulation anomaly or multi-format file header."
            )
        )

    # 2. Dimension concordance: actual pixels vs EXIF recorded dimensions
    if camera_meta and camera_meta.metadata_dimensions:
        meta_w = camera_meta.metadata_dimensions.get("width")
        meta_h = camera_meta.metadata_dimensions.get("height")
        if meta_w and meta_h:
            if meta_w != validation_result.width or meta_h != validation_result.height:
                observations.append(
                    ConsistencyObservation(
                        check_name="dimension_concordance",
                        severity=ConsistencySeverity.INCONSISTENCY,
                        observed_state=(
                            f"Decoded dimensions ({validation_result.width}x{validation_result.height}) "
                            f"differ from EXIF metadata dimensions ({meta_w}x{meta_h})"
                        ),
                        benign_explanation=(
                            "The image was cropped, resized, or re-saved by an application that updated the image raster "
                            "without rewriting the ExifImageWidth/ExifImageHeight tags."
                        )
                    )
                )

    # 3. Orientation vs image geometry
    if camera_meta and camera_meta.orientation_tag:
        otag = camera_meta.orientation_tag
        if otag in [5, 6, 7, 8]:
            # Tag indicates vertical/portrait rotation from landscape sensor
            aspect = "portrait" if validation_result.height > validation_result.width else "landscape"
            observations.append(
                ConsistencyObservation(
                    check_name="orientation_geometry_concordance",
                    severity=ConsistencySeverity.INFO,
                    observed_state=f"EXIF orientation is tag {otag} ({camera_meta.orientation_description}), raster is {aspect} ({validation_result.width}x{validation_result.height})",
                    benign_explanation="Standard camera orientation metadata tagging unrotated sensor readout."
                )
            )

    # 4. Timestamp chronology: capture vs modification
    if camera_meta and camera_meta.date_time_original and camera_meta.date_time_modified:
        dto = camera_meta.date_time_original
        dtm = camera_meta.date_time_modified
        # Standard EXIF format: YYYY:MM:DD HH:MM:SS
        if len(dto) >= 19 and len(dtm) >= 19:
            # Lexicographical comparison holds for standardized YYYY:MM:DD HH:MM:SS
            if dto > dtm:
                observations.append(
                    ConsistencyObservation(
                        check_name="timestamp_chronology",
                        severity=ConsistencySeverity.INCONSISTENCY,
                        observed_state=f"Capture timestamp ('{dto}') is chronologically after modification timestamp ('{dtm}')",
                        benign_explanation=(
                            "Camera clock desynchronization, improper manual clock adjustment, or batch timezone editing "
                            "in photo management utilities."
                        )
                    )
                )

    # 5. Software indicators
    if camera_meta and camera_meta.software:
        sw_lower = camera_meta.software.lower()
        matched = [k for k in EDITING_SOFTWARE_KEYWORDS if k in sw_lower]
        if matched:
            observations.append(
                ConsistencyObservation(
                    check_name="software_editing_indicator",
                    severity=ConsistencySeverity.INFO,
                    observed_state=f"Software tag identifies post-processing or authoring application: '{camera_meta.software}'",
                    benign_explanation="Routine photo editing, digital asset management export, or color grading workflow."
                )
            )

    # 6. Thumbnail consistency
    if thumbnail_result.has_thumbnail and thumbnail_result.thumbnail_dimensions:
        tw = thumbnail_result.thumbnail_dimensions.get("width", 0)
        th = thumbnail_result.thumbnail_dimensions.get("height", 0)
        pw = validation_result.width
        ph = validation_result.height
        if tw >= pw or th >= ph:
            observations.append(
                ConsistencyObservation(
                    check_name="thumbnail_dimension_concordance",
                    severity=ConsistencySeverity.INCONSISTENCY,
                    observed_state=f"Embedded thumbnail dimensions ({tw}x{th}) are equal to or larger than primary image ({pw}x{ph})",
                    benign_explanation="Malformed thumbnail stream or unconventional container packaging."
                )
            )

        if thumbnail_result.thumbnail_aspect_ratio and thumbnail_result.primary_aspect_ratio:
            ar_diff = abs(thumbnail_result.thumbnail_aspect_ratio - thumbnail_result.primary_aspect_ratio)
            if ar_diff > 0.15:
                observations.append(
                    ConsistencyObservation(
                        check_name="thumbnail_aspect_ratio_concordance",
                        severity=ConsistencySeverity.INFO,
                        observed_state=(
                            f"Thumbnail aspect ratio ({thumbnail_result.thumbnail_aspect_ratio:.2f}) "
                            f"diverges from primary image aspect ratio ({thumbnail_result.primary_aspect_ratio:.2f})"
                        ),
                        benign_explanation="Primary image was cropped without regenerating the embedded thumbnail preview."
                    )
                )

    inconsistencies = [o for o in observations if o.severity == ConsistencySeverity.INCONSISTENCY]
    status = "DISCREPANCIES_OBSERVED" if inconsistencies else "CONSISTENT"

    notes = (
        "Consistency checks evaluate container geometry, timestamp chronology, metadata dimensions, and embedded thumbnails. "
        "Discrepancies frequently occur from benign causes including non-destructive cropping, social media recompression, "
        "clock drift, or standard editing tools. Discrepancies alone do not establish malicious tampering or synthetic generation."
    )

    return ContainerConsistencyResult(
        status=status,
        observations=observations,
        notes=notes,
    )


def inspect_metadata(
    image: Image.Image,
    raw_bytes: bytes,
    validation_result: ImageValidationResult,
    allow_gps_extraction: bool = False,
) -> MetadataForensicResult:
    """
    Perform safe, privacy-aware metadata extraction, thumbnail analysis, and container consistency inspection.
    """
    try:
        return _inspect_metadata_internal(image, raw_bytes, validation_result, allow_gps_extraction)
    except Exception as exc:
        inv = MetadataInventory(
            status=MetadataStatus.ANALYSIS_FAILED,
            detected_structures=[],
            exif_tag_count=0,
            xmp_packet_present=False,
            png_text_chunks_count=0,
        )
        return MetadataForensicResult(
            inventory=inv,
            camera_metadata=None,
            gps_summary=GPSMetadataSummary(gps_present=False, gps_status="ABSENT", tag_count=0, coordinates_redacted=True),
            thumbnail_analysis=ThumbnailAnalysisResult(status=ThumbnailStatus.ANALYSIS_FAILED, has_thumbnail=False, comparison_notes=f"Metadata analysis failed: {str(exc)}"),
            container_consistency=ContainerConsistencyResult(status="NOT_EVALUATED", observations=[], notes="Consistency evaluation was skipped due to parser failure."),
            analysis_notes=f"Metadata extraction failed with error: {type(exc).__name__}",
        )


def _inspect_metadata_internal(
    image: Image.Image,
    raw_bytes: bytes,
    validation_result: ImageValidationResult,
    allow_gps_extraction: bool = False,
) -> MetadataForensicResult:
    detected_structures: List[str] = []
    exif_tag_count = 0
    png_text_count = 0
    xmp_packet_present = False
    metadata_status = MetadataStatus.ABSENT

    # 1. Detect XMP packet
    if (b"http://ns.adobe.com/xap/1.0/" in raw_bytes) or (b"XML:com.adobe.xmp" in raw_bytes):
        xmp_packet_present = True
        detected_structures.append("XMP")

    # 2. Extract PNG text chunks if applicable
    png_text = getattr(image, "text", {})
    if isinstance(png_text, dict) and len(png_text) > 0:
        png_text_count = len(png_text)
        detected_structures.append("PNG_TEXT")

    # 3. Extract EXIF tags
    exif_obj = None
    sub_exif = {}
    gps_ifd = {}
    is_malformed_exif = False

    try:
        raw_exif_data = image.getexif()
        if raw_exif_data is not None:
            exif_obj = raw_exif_data
            exif_tag_count = len(exif_obj)
            if exif_tag_count > 0:
                detected_structures.append("EXIF")

            try:
                sub_exif = exif_obj.get_ifd(ExifTags.IFD.Exif)
            except Exception:
                is_malformed_exif = True

            try:
                gps_ifd = exif_obj.get_ifd(ExifTags.IFD.GPSInfo)
            except Exception:
                is_malformed_exif = True

    except Exception:
        is_malformed_exif = True

    # Check raw exif presence if getexif returned empty
    raw_exif_bytes = image.info.get("exif")
    if raw_exif_bytes and not exif_tag_count:
        # EXIF bytes present but zero tags extracted -> potentially malformed or unsupported
        is_malformed_exif = True

    # Determine overall metadata status
    if is_malformed_exif and not detected_structures:
        metadata_status = MetadataStatus.MALFORMED
    elif detected_structures:
        metadata_status = MetadataStatus.PARTIAL if is_malformed_exif else MetadataStatus.PRESENT
    else:
        metadata_status = MetadataStatus.ABSENT

    inventory = MetadataInventory(
        status=metadata_status,
        detected_structures=detected_structures,
        exif_tag_count=exif_tag_count,
        xmp_packet_present=xmp_packet_present,
        png_text_chunks_count=png_text_count,
    )

    # 4. Extract Camera & Recording Metadata with Truthful Device Identification (Mission 22)
    camera_metadata: Optional[CameraMetadata] = None
    orientation_val: Optional[int] = None

    make = None
    model = None
    software = None
    lens_model = None
    dto = None
    dtd = None
    dtm = None
    offset_time = None
    meta_dims = None

    # Parse raw bytes directly with secondary PIL instance to avoid stripped in-memory handles
    try:
        raw_stream_img = Image.open(io.BytesIO(raw_bytes))
        raw_exif_tags = raw_stream_img.getexif()
        if raw_exif_tags:
            if not exif_obj:
                exif_obj = raw_exif_tags
            else:
                for k, v in raw_exif_tags.items():
                    if k not in exif_obj:
                        exif_obj[k] = v
            if not sub_exif:
                try:
                    sub_exif = raw_exif_tags.get_ifd(ExifTags.IFD.Exif)
                except Exception:
                    pass
    except Exception:
        pass

    if exif_obj:
        make = _safe_str(exif_obj.get(ExifTags.Base.Make) or exif_obj.get(271))
        model = _safe_str(exif_obj.get(ExifTags.Base.Model) or exif_obj.get(272))
        software = _safe_str(exif_obj.get(ExifTags.Base.Software) or exif_obj.get(305))
        dtm = _safe_str(exif_obj.get(ExifTags.Base.DateTime) or exif_obj.get(306))

        raw_orient = exif_obj.get(ExifTags.Base.Orientation) or exif_obj.get(274)
        if isinstance(raw_orient, int) and 1 <= raw_orient <= 8:
            orientation_val = raw_orient

        if sub_exif:
            dto = _safe_str(sub_exif.get(ExifTags.Base.DateTimeOriginal) or sub_exif.get(36867))
            dtd = _safe_str(sub_exif.get(ExifTags.Base.DateTimeDigitized) or sub_exif.get(36868))
            lens_model = _safe_str(sub_exif.get(ExifTags.Base.LensModel) or sub_exif.get(42036))
            offset_time = _safe_str(
                sub_exif.get(ExifTags.Base.OffsetTimeOriginal) or sub_exif.get(36881) or sub_exif.get(ExifTags.Base.OffsetTime)
            )

            mw = sub_exif.get(ExifTags.Base.ExifImageWidth) or exif_obj.get(ExifTags.Base.ImageWidth) or exif_obj.get(256)
            mh = sub_exif.get(ExifTags.Base.ExifImageHeight) or exif_obj.get(ExifTags.Base.ImageLength) or exif_obj.get(257)
            if isinstance(mw, int) and isinstance(mh, int) and mw > 0 and mh > 0:
                meta_dims = {"width": mw, "height": mh}

    # Fallback to PNG text if software is absent
    if not software and png_text_count > 0 and isinstance(png_text, dict):
        software = _safe_str(png_text.get("Software") or png_text.get("Comment") or png_text.get("Description"))

    orient_desc = ORIENTATION_DESCRIPTIONS.get(orientation_val) if orientation_val else None

    # Determine truthful device status and consumer display text (Mission 22 Rule)
    if is_malformed_exif and not make and not model:
        dev_status = DeviceMetadataStatus.MALFORMED
        dev_display = "Device metadata could not be read"
    elif make and model:
        dev_status = DeviceMetadataStatus.PRESENT
        # Prevent duplicated brand in model (e.g. 'Sony Sony ILCE-7M3')
        if model.lower().startswith(make.lower()):
            dev_display = model
        else:
            dev_display = f"{make} {model}"
    elif make and not model:
        dev_status = DeviceMetadataStatus.MANUFACTURER_ONLY
        dev_display = f"{make} (Model unavailable)"
    elif software and not make and not model:
        dev_status = DeviceMetadataStatus.SOFTWARE_ONLY
        dev_display = f"Software: {software}"
    else:
        dev_status = DeviceMetadataStatus.ABSENT
        dev_display = "Device information not present in file"

    camera_metadata = CameraMetadata(
        make=make,
        model=model,
        lens_model=lens_model,
        software=software,
        orientation_tag=orientation_val,
        orientation_description=orient_desc,
        date_time_original=dto,
        date_time_digitized=dtd,
        date_time_modified=dtm,
        offset_time=offset_time,
        metadata_dimensions=meta_dims,
        device_status=dev_status,
        device_display_text=dev_display,
        provenance_note="Metadata can be edited or stripped; presence of camera tags does not establish legal authenticity.",
    )

    # 5. Privacy-Aware GPS Handling
    gps_tag_count = len(gps_ifd) if gps_ifd else 0
    gps_present = gps_tag_count > 0

    gps_summary = GPSMetadataSummary(
        gps_present=gps_present,
        gps_status="DETECTED_AND_REDACTED" if gps_present else "ABSENT",
        tag_count=gps_tag_count,
        coordinates_redacted=True,
        latitude=None,
        longitude=None,
        privacy_notice=(
            "GPS coordinates are redacted by default to protect individual privacy. "
            "Detection indicates only that geolocation tags exist in the container."
        ),
    )

    # 6. Embedded Thumbnail Analysis
    thumbnail_result = analyze_embedded_thumbnail(image, orientation_tag=orientation_val)

    # 7. Container and Metadata Consistency Checks
    consistency_result = _check_container_consistency(
        image=image,
        validation_result=validation_result,
        camera_meta=camera_metadata,
        thumbnail_result=thumbnail_result,
    )

    notes = (
        "Camera make, model, software, and timestamp tags are user-editable metadata fields and do not constitute "
        "cryptographic proof of origin or authenticity. Absence of metadata is standard for web, messaging, and "
        "social media platforms and must never be interpreted as evidence of synthetic generation or malicious tampering."
    )

    return MetadataForensicResult(
        inventory=inventory,
        camera_metadata=camera_metadata,
        gps_summary=gps_summary,
        thumbnail_analysis=thumbnail_result,
        container_consistency=consistency_result,
        analysis_notes=notes,
    )
