import numpy as np

class CubicSplineKernel:
    """
    Standard Cubic Spline Kernel for SPH.
    """
    def __init__(self, h: float, dim: int = 2):
        self.h = h
        self.dim = dim
        
        # Normalization factor
        if self.dim == 2:
            self.alpha = 10.0 / (7.0 * np.pi * (h**2))
        elif self.dim == 3:
            self.alpha = 1.0 / (np.pi * (h**3))
        else:
            raise NotImplementedError("Only 2D and 3D cubic spline kernels are implemented.")
            
    def W(self, r: np.ndarray) -> np.ndarray:
        """
        Vectorized kernel evaluation.
        """
        is_scalar = np.isscalar(r) or (isinstance(r, np.ndarray) and r.ndim == 0)
        r_arr = np.asarray(r) if not is_scalar else np.array([r])
        
        q = r_arr / self.h
        
        result = np.zeros_like(r_arr, dtype=np.float64)
        
        mask1 = (q >= 0.0) & (q < 1.0)
        mask2 = (q >= 1.0) & (q < 2.0)
        
        q1 = q[mask1]
        result[mask1] = self.alpha * (1.0 - 1.5 * q1**2 + 0.75 * q1**3)
        
        q2 = q[mask2]
        result[mask2] = self.alpha * 0.25 * (2.0 - q2)**3
        
        return result[0] if is_scalar else result

    def grad_W(self, r_vec: np.ndarray, r: np.ndarray) -> np.ndarray:
        """
        Vectorized gradient of the kernel.
        """
        is_scalar = np.isscalar(r) or (isinstance(r, np.ndarray) and r.ndim == 0)
        r_arr = np.asarray(r) if not is_scalar else np.array([r])
        r_vec_arr = np.asarray(r_vec) if not is_scalar else np.array([r_vec])
        
        q = r_arr / self.h
        
        grad_factor = np.zeros_like(r_arr, dtype=np.float64)
        
        mask1 = (q > 0.0) & (q < 1.0)
        mask2 = (q >= 1.0) & (q < 2.0)
        
        q1 = q[mask1]
        grad_factor[mask1] = self.alpha * (-3.0 * q1 + 2.25 * q1**2) / self.h
        
        q2 = q[mask2]
        grad_factor[mask2] = self.alpha * (-0.75 * (2.0 - q2)**2) / self.h
        
        # Avoid division by zero
        safe_r = np.where(r_arr > 0, r_arr, 1.0)
        
        grad_div_r = grad_factor / safe_r
        result = grad_div_r[:, np.newaxis] * r_vec_arr
            
        return result[0] if is_scalar else result
