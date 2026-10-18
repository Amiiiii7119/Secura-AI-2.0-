import base64
import io
from typing import Optional
import numpy as np
from PIL import Image

from app.schemas.evidence import NoiseResidualMetrics, NoiseResidualResult


class NoiseResidualError(Exception):
    def __init__(self, message: str, error_code: str = "NOISE_RESIDUAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def perform_noise_residual_analysis(image: Image.Image) -> NoiseResidualResult:
    """Perform high-pass spatial residual analysis using a 3x3 discrete Laplacian operator.
    
    Forensic Methodology:
    High-pass spatial filtering isolates fine residual variations by subtracting a local linear
    predictor from the image luminance.
    
    The local predictor calculates the average of the 4-connected spatial neighbors:
        I_pred(y, x) = 0.25 * [I(y-1, x) + I(y+1, x) + I(y, x-1) + I(y, x+1)]
    The normalized Laplacian spatial residual is:
        R(y, x) = I(y, x) - I_pred(y, x)
    
    Spatial High-Pass SNR Proxy:
    The SNR proxy is computed as 10 * log10(Var(center_signal) / max(Var(residual), 1e-6)).
    This is a deterministic mathematical proxy of spatial high-frequency energy relative to local
    signal variance; it is NOT a physical camera sensor noise or Photo-Response Non-Uniformity
    (PRNU) calibrated measurement.
    
    Important Forensic Limitations:
    - Highly textured surfaces naturally produce higher residual magnitudes than flat areas.
    - Denoising, bilateral filtering, sharpening, and JPEG compression strongly alter residuals.
    - Residual variance is an investigative signal and does NOT prove synthetic AI generation.
    """
    try:
        width, height = image.size
        
        # Guard: Minimum dimensions for 3x3 spatial filter
        if width < 3 or height < 3:
            return NoiseResidualResult(
                status="UNAVAILABLE",
                metrics=None,
                visualization_data_url=None,
                analysis_notes=(
                    f"Image dimensions ({width}x{height}) are smaller than the minimum 3x3 pixel kernel "
                    "required for local spatial prediction and noise residual estimation."
                )
            )
        
        # Step 1: Safe luminance conversion with alpha composite protection
        if image.mode != "RGB":
            if image.mode in ("RGBA", "LA") or ("transparency" in image.info):
                canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
                canvas.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
                luma_img = canvas.convert("L")
            else:
                luma_img = image.convert("L")
        else:
            luma_img = image.convert("L")
            
        luma = np.asarray(luma_img, dtype=np.float32)
        
        # Step 2: Compute 3x3 Laplacian normalized high-pass residual
        # R = I(y, x) - 0.25 * [I(y-1, x) + I(y+1, x) + I(y, x-1) + I(y, x+1)]
        residual = np.zeros_like(luma)
        center = luma[1:-1, 1:-1]
        neighbors = (
            luma[0:-2, 1:-1] +
            luma[2:, 1:-1] +
            luma[1:-1, 0:-2] +
            luma[1:-1, 2:]
        ) * 0.25
        
        # Inner valid region
        res_inner = center - neighbors
        residual[1:-1, 1:-1] = res_inner
        
        # Step 3: Statistical metrics computed over the inner valid region
        mean_abs = float(np.mean(np.abs(res_inner)))
        std_res = float(np.std(res_inner))
        max_res = float(np.max(np.abs(res_inner)))
        noise_energy = float(np.mean(res_inner ** 2))
        
        # Estimate Spatial High-Pass SNR Proxy in dB
        var_signal = float(np.var(center))
        epsilon = 1e-6
        if noise_energy > epsilon and var_signal > epsilon:
            snr_db = round(float(10.0 * np.log10(var_signal / noise_energy)), 2)
        else:
            snr_db = None
            
        # Step 4: Visual Residual Map (centered at neutral gray 128)
        # Scaled by 5.0x for visual contrast enhancement
        vis_arr = np.clip(128.0 + res_inner * 5.0, 0, 255).astype(np.uint8)
        vis_full = np.full((height, width), 128, dtype=np.uint8)
        vis_full[1:-1, 1:-1] = vis_arr
        
        vis_img = Image.fromarray(vis_full, mode="L")
        buf = io.BytesIO()
        vis_img.save(buf, format="PNG")
        buf.seek(0)
        b64_str = base64.b64encode(buf.getvalue()).decode("ascii")
        vis_url = f"data:image/png;base64,{b64_str}"
        
        metrics = NoiseResidualMetrics(
            filter_type="3x3 Discrete Laplacian High-Pass Operator",
            mean_absolute_residual=round(mean_abs, 4),
            std_residual=round(std_res, 4),
            max_residual=round(max_res, 4),
            noise_energy=round(noise_energy, 4),
            snr_estimate_db=snr_db
        )
        
        notes = (
            f"Extracted high-frequency spatial residual using 3x3 local prediction filter across {width}x{height} px. "
            f"Mean absolute residual is {mean_abs:.4f} with standard deviation {std_res:.4f} (residual energy: {noise_energy:.2f}). "
        )
        if snr_db is not None:
            notes += f"Spatial high-pass SNR proxy is {snr_db:.1f} dB. "
        if mean_abs < 0.8:
            notes += "Low residual magnitude suggests strong smoothing, heavy bilateral filtering, or synthetic flat generation. "
        elif mean_abs > 5.0:
            notes += "Elevated residual magnitude reflects pronounced high-frequency textures, sharpening, or grain. "
        else:
            notes += "Residual magnitude falls within standard photographic ranges. "
        notes += (
            "This metric is a mathematical proxy of high-frequency variance, not a calibrated physical sensor PRNU "
            "measurement; texture, lighting, and compression strongly influence residuals."
        )
        
        return NoiseResidualResult(
            status="SUCCESS",
            metrics=metrics,
            visualization_data_url=vis_url,
            analysis_notes=notes
        )
        
    except Exception as exc:
        raise NoiseResidualError(f"High-pass noise residual analysis failed: {str(exc)}")
