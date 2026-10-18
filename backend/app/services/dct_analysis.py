import base64
import io
from typing import Optional, Tuple
import numpy as np
from PIL import Image

from app.schemas.evidence import DCTForensicResult, DCTMetrics


class DCTAnalysisError(Exception):
    def __init__(self, message: str, error_code: str = "DCT_ANALYSIS_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def _build_dct_matrix(n: int = 8) -> np.ndarray:
    """Generate the standard 1D orthonormal DCT-II basis matrix of size n x n."""
    matrix = np.zeros((n, n), dtype=np.float32)
    for u in range(n):
        alpha = np.sqrt(1.0 / n) if u == 0 else np.sqrt(2.0 / n)
        for x in range(n):
            matrix[u, x] = alpha * np.cos(np.pi * (2 * x + 1) * u / (2.0 * n))
    return matrix


# Cache the 8x8 DCT matrix
_DCT_8x8 = _build_dct_matrix(8)


def perform_dct_analysis(image: Image.Image) -> DCTForensicResult:
    """Perform Discrete Cosine Transform (DCT) and 8x8 block-boundary artifact analysis.
    
    Forensic Methodology:
    Standard JPEG compression segments images into 8x8 spatial pixel blocks and applies
    frequency quantization independently per block. This introduces step discontinuities
    across the 8x8 block grid boundaries (columns x = 8k and rows y = 8k) relative to
    smooth transitions within internal block pixels.
    
    This function measures:
    1. Boundary Discontinuity: Mean absolute difference across adjacent pixels at 8x8 boundaries.
    2. Internal Discontinuity: Mean absolute difference across non-boundary adjacent pixels (reference baseline).
    3. Blocking Artifact Ratio (BAR): Ratio of boundary to internal discontinuity. Values > 1.0 indicate
       systematic grid step discontinuities typical of lossy JPEG compression or inherited block structures.
    4. Mean Block AC Energy: Average high-frequency energy computed via 2D orthonormal 8x8 DCT.
    
    Limitations:
    - JPEG compression naturally produces block artifacts; elevated BAR is NOT proof of tampering or AI synthesis.
    - Splicing, cropping, or resizing may shift, misalign, or smooth the grid.
    - PNG files may carry inherited block artifacts if previously saved as JPEG.
    """
    try:
        width, height = image.size
        
        # Guard: Minimum dimensions for 8x8 block analysis
        if width < 8 or height < 8:
            return DCTForensicResult(
                status="UNAVAILABLE",
                metrics=None,
                visualization_data_url=None,
                analysis_notes=(
                    f"Image dimensions ({width}x{height}) are smaller than the minimum 8x8 pixel block grid "
                    "required for discrete cosine transform and block-boundary discontinuity analysis."
                )
            )
        
        # Step 1: Safe luminance extraction
        if image.mode != "RGB":
            if image.mode in ("RGBA", "LA") or ("transparency" in image.info):
                canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
                canvas.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
                luma_img = canvas.convert("L")
            else:
                luma_img = image.convert("L")
        else:
            luma_img = image.convert("L")
        
        luma_arr = np.asarray(luma_img, dtype=np.float32)
        
        # Step 2: Handle dimensions not divisible by 8 cleanly
        grid_w = width - (width % 8)
        grid_h = height - (height % 8)
        blocks_x = grid_w // 8
        blocks_y = grid_h // 8
        total_blocks = blocks_x * blocks_y
        
        if total_blocks == 0:
            return DCTForensicResult(
                status="UNAVAILABLE",
                metrics=None,
                visualization_data_url=None,
                analysis_notes="Unable to construct a valid 8x8 block grid from asset dimensions."
            )
        
        active_grid = luma_arr[:grid_h, :grid_w]
        
        # Step 3: Compute boundary step discontinuities vs internal reference steps
        # Horizontal boundaries (between row 8k-1 and 8k)
        horiz_boundary_diffs = []
        horiz_internal_diffs = []
        for r in range(1, grid_h):
            diff = np.abs(active_grid[r, :] - active_grid[r - 1, :])
            if r % 8 == 0:
                horiz_boundary_diffs.append(diff)
            elif r % 8 == 4:
                horiz_internal_diffs.append(diff)
                
        # Vertical boundaries (between col 8k-1 and 8k)
        vert_boundary_diffs = []
        vert_internal_diffs = []
        for c in range(1, grid_w):
            diff = np.abs(active_grid[:, c] - active_grid[:, c - 1])
            if c % 8 == 0:
                vert_boundary_diffs.append(diff)
            elif c % 8 == 4:
                vert_internal_diffs.append(diff)
        
        all_boundary = []
        if horiz_boundary_diffs:
            all_boundary.append(np.concatenate(horiz_boundary_diffs))
        if vert_boundary_diffs:
            all_boundary.append(np.concatenate(vert_boundary_diffs))
            
        all_internal = []
        if horiz_internal_diffs:
            all_internal.append(np.concatenate(horiz_internal_diffs))
        if vert_internal_diffs:
            all_internal.append(np.concatenate(vert_internal_diffs))
            
        boundary_disc = float(np.mean(np.concatenate(all_boundary))) if all_boundary else 0.0
        internal_disc = float(np.mean(np.concatenate(all_internal))) if all_internal else 0.0
        
        # Avoid division by zero on uniform/flat imagery
        epsilon = 1e-4
        blocking_ratio = min(float(boundary_disc / max(internal_disc, epsilon)), 999.9999)
        
        # Step 4: 2D 8x8 DCT Block AC Energy
        # Reshape into (blocks_y, 8, blocks_x, 8) -> (total_blocks, 8, 8)
        blocks = active_grid.reshape(blocks_y, 8, blocks_x, 8).transpose(0, 2, 1, 3).reshape(total_blocks, 8, 8)
        
        # 2D DCT: C = T @ B @ T.T for each block
        dct_blocks = np.matmul(np.matmul(_DCT_8x8, blocks), _DCT_8x8.T)
        
        # AC coefficients are all except (0, 0) DC component
        # Zero out DC component to isolate AC frequency variation
        dct_ac = dct_blocks.copy()
        dct_ac[:, 0, 0] = 0.0
        ac_energy_per_block = np.sum(dct_ac ** 2, axis=(1, 2)) / 64.0
        mean_ac_energy = float(np.mean(ac_energy_per_block))
        
        # Step 5: Visual Block-Artifact Map
        # Create a spatial visualization map highlighting 8x8 block boundary locations
        # and their local step magnitude
        vis_map = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Base luminance in dark tones
        luma_norm = np.clip(luma_arr * 0.4, 0, 100).astype(np.uint8)
        vis_map[:, :, 0] = luma_norm
        vis_map[:, :, 1] = luma_norm
        vis_map[:, :, 2] = luma_norm
        
        # Highlight 8x8 block boundary lines with cyan/yellow intensity based on boundary step
        for r in range(8, grid_h, 8):
            step_mag = np.clip(np.abs(active_grid[r, :] - active_grid[r - 1, :]) * 6.0, 40, 255).astype(np.uint8)
            vis_map[r, :grid_w, 0] = np.maximum(vis_map[r, :grid_w, 0], (step_mag * 0.2).astype(np.uint8))
            vis_map[r, :grid_w, 1] = np.maximum(vis_map[r, :grid_w, 1], (step_mag * 0.8).astype(np.uint8))
            vis_map[r, :grid_w, 2] = np.maximum(vis_map[r, :grid_w, 2], step_mag)
            
        for c in range(8, grid_w, 8):
            step_mag = np.clip(np.abs(active_grid[:, c] - active_grid[:, c - 1]) * 6.0, 40, 255).astype(np.uint8)
            vis_map[:grid_h, c, 0] = np.maximum(vis_map[:grid_h, c, 0], (step_mag * 0.2).astype(np.uint8))
            vis_map[:grid_h, c, 1] = np.maximum(vis_map[:grid_h, c, 1], (step_mag * 0.8).astype(np.uint8))
            vis_map[:grid_h, c, 2] = np.maximum(vis_map[:grid_h, c, 2], step_mag)
            
        # Encode visualization map as in-memory PNG
        vis_img = Image.fromarray(vis_map, mode="RGB")
        buf = io.BytesIO()
        vis_img.save(buf, format="PNG")
        buf.seek(0)
        b64_str = base64.b64encode(buf.getvalue()).decode("ascii")
        vis_url = f"data:image/png;base64,{b64_str}"
        
        metrics = DCTMetrics(
            block_size=8,
            analyzed_width=grid_w,
            analyzed_height=grid_h,
            total_blocks=total_blocks,
            boundary_discontinuity=round(boundary_disc, 4),
            internal_discontinuity=round(internal_disc, 4),
            blocking_artifact_ratio=round(blocking_ratio, 4),
            mean_block_energy=round(mean_ac_energy, 4)
        )
        
        notes = (
            f"Analyzed {total_blocks:,} 8x8 spatial blocks across {grid_w}x{grid_h} px. "
            f"Blocking Artifact Ratio is {blocking_ratio:.4f} (boundary: {boundary_disc:.2f}, internal: {internal_disc:.2f}). "
        )
        if width != grid_w or height != grid_h:
            notes += f"Remainder pixels ({width - grid_w}x, {height - grid_h}y) beyond 8x8 multiples were omitted from block statistics. "
        if blocking_ratio > 1.2:
            notes += "Elevated ratio indicates pronounced 8x8 grid boundary steps consistent with lossy JPEG quantization or recompression. "
        elif blocking_ratio < 0.95:
            notes += "Ratio below 1.0 indicates absence of primary 8x8 grid alignment, common in uncompressed, rescaled, or non-JPEG imagery. "
        else:
            notes += "Ratio near 1.0 indicates uniform continuity between block boundaries and internal pixels. "
        notes += "This signal measures compression grid alignment and does not constitute proof of origin or artificial synthesis."
        
        return DCTForensicResult(
            status="SUCCESS",
            metrics=metrics,
            visualization_data_url=vis_url,
            analysis_notes=notes
        )
        
    except Exception as exc:
        raise DCTAnalysisError(f"DCT block-artifact analysis encountered an unexpected error: {str(exc)}")
