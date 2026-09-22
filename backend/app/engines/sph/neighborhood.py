from scipy.spatial import cKDTree
import numpy as np

class NeighborSearch:
    """
    Handles spatial indexing and neighborhood queries using cKDTree.
    """
    def __init__(self, search_radius: float):
        self.search_radius = search_radius
        self.tree = None

    def build_tree(self, positions: np.ndarray) -> None:
        """
        Builds the KD-Tree from particle positions.
        """
        self.tree = cKDTree(positions)

    def query_pairs(self):
        """
        Queries all neighbor pairs within the search radius.
        Returns a tuple of (i_indices, j_indices) arrays.
        """
        if self.tree is None:
            raise ValueError("Tree not built. Call build_tree first.")
            
        # query_pairs returns a set of (i, j) where i < j
        pairs = self.tree.query_pairs(self.search_radius, output_type='ndarray')
        
        if len(pairs) == 0:
            return np.array([], dtype=np.int32), np.array([], dtype=np.int32)
            
        i = pairs[:, 0]
        j = pairs[:, 1]
        
        # Since SPH is symmetric but we need bidirectional interactions for vectorized scatter ops:
        # Create full directional pairs (i->j and j->i)
        i_full = np.concatenate([i, j])
        j_full = np.concatenate([j, i])
        
        return i_full, j_full
