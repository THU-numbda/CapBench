#!/usr/bin/env python3

"""
cap3d_mesh.py

Build a triangular surface mesh from a CAP3D file using the Gmsh Python API.

- Input: CAP3D file (example structure: <conductor> contains <block> entries
  with basepoint(), v1(), v2(), hvector())
- Output: A 2D surface mesh (triangles) of all conductor solids, written as
  a Gmsh mesh file named <input>.msh

Notes
- Units: CAP3D samples typically use micrometers. This script scales geometry
  so that 1 nm = 1 model unit (i.e., µm × 1e3) for robust CAD operations.
- Adaptivity: Enabled by default (edge-distance field), with automatic size
  settings derived from the model dimensions (diagonal / --diag-divisor).
- Triangles only: Uses Frontal-Delaunay 2D mesher and disables recombination.

Dependencies
- gmsh (Python API). Install with: conda install -n klayout-net -c conda-forge gmsh

"""

import argparse
import math
import os
import sys
import time
from typing import Dict, List, Tuple
import gmsh
from tqdm import tqdm 
from window_tools.cap3d_parser import StreamingCap3DParser


def parse_cap3d(path: str) -> Dict[str, List[Dict[str, Tuple[float, float, float]]]]:
    """
    Parse a CAP3D file using the repository's utils.cap3d_parser and
    return a dict mapping conductor name -> list of block dicts with
    basepoint, v1, v2, hvector.
    """
    parser = StreamingCap3DParser(path)
    conductors: Dict[str, List[Dict[str, Tuple[float, float, float]]]] = {}
    for blk in parser.parse_blocks_streaming():
        # Only mesh conductor blocks
        if getattr(blk, 'type', None) != 'conductor':
            continue
        cond_name = getattr(blk, 'parent_name', 'COND')
        conductors.setdefault(cond_name, [])
        # Convert numpy arrays to tuples of floats
        base = tuple(float(x) for x in blk.base.tolist())
        v1 = tuple(float(x) for x in blk.v1.tolist())
        v2 = tuple(float(x) for x in blk.v2.tolist())
        hvec = tuple(float(x) for x in blk.hvec.tolist())
        conductors[cond_name].append({
            'basepoint': base,
            'v1': v1,
            'v2': v2,
            'hvector': hvec,
        })

    if not conductors:
        raise ValueError(f"No conductor blocks found in {path}")
    return conductors


def parse_args(argv: List[str]) -> argparse.Namespace:
    """
    Parse CLI arguments for the mesh generator.
    """
    parser = argparse.ArgumentParser(
        description="Build a surface mesh from a CAP3D file using Gmsh.",
    )
    parser.add_argument(
        "input",
        help="Path to the input .cap3d file.",
    )
    parser.add_argument(
        "--diag-divisor",
        type=float,
        default=60.0,
        help="Divide the model diagonal by this value to derive Mesh.CharacteristicLengthMax.",
    )
    parser.add_argument(
        "--no-union",
        action="store_true",
        help="Disable boolean union of overlapping blocks (faster but may produce overlapping surfaces).",
    )
    parser.add_argument(
        "--show-normals",
        action="store_true",
        help="Visualize triangle normal vectors in Gmsh viewer (displayed as arrows).",
    )
    parser.add_argument(
        "--normal-scale",
        type=float,
        default=0.5,
        help="Scale factor for normal vector length relative to average edge length (default: 0.5).",
    )
    args = parser.parse_args(argv)

    if args.diag_divisor <= 0:
        parser.error("--diag-divisor must be positive")

    return args


def _vec_norm(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])


def add_volume_from_block(occ, base: Tuple[float, float, float], v1: Tuple[float, float, float],
                          v2: Tuple[float, float, float], hv: Tuple[float, float, float]) -> int:
    """
    Build a volume by extruding a parallelogram (base, base+v1, base+v1+v2, base+v2) along hvector hv.
    Returns OCC volume tag.
    """
    # Fast path: axis-aligned blocks -> use addBox for robustness at tiny scales
    # Use more forgiving tolerance (1e-9 in nm units = 1e-12 µm = 1 fm)
    axis_eps = 1e-9
    is_axis_aligned = (
        abs(v1[1]) < axis_eps and abs(v1[2]) < axis_eps and
        abs(v2[0]) < axis_eps and abs(v2[2]) < axis_eps and
        abs(hv[0]) < axis_eps and abs(hv[1]) < axis_eps
    )

    if is_axis_aligned:
        dx = v1[0]
        dy = v2[1]
        dz = hv[2]
        # Normalize to positive lengths; shift base to the min corner
        x0 = base[0] if dx >= 0 else base[0] + dx
        y0 = base[1] if dy >= 0 else base[1] + dy
        z0 = base[2] if dz >= 0 else base[2] + dz
        vol = occ.addBox(x0, y0, z0, abs(dx), abs(dy), abs(dz))
        return vol

    # General path: build base parallelogram and extrude along hv
    c00 = base
    c10 = (base[0] + v1[0], base[1] + v1[1], base[2] + v1[2])
    c11 = (c10[0] + v2[0], c10[1] + v2[1], c10[2] + v2[2])
    c01 = (base[0] + v2[0], base[1] + v2[1], base[2] + v2[2])

    # Guard against degenerate blocks
    eps = 1e-18
    if _vec_norm(v1) < eps or _vec_norm(v2) < eps or _vec_norm(hv) < eps:
        raise ValueError("Degenerate block: one of v1,v2,hvector has zero length")

    # Create points
    p00 = occ.addPoint(*c00)
    p10 = occ.addPoint(*c10)
    p11 = occ.addPoint(*c11)
    p01 = occ.addPoint(*c01)

    # Create lines and wire
    l1 = occ.addLine(p00, p10)
    l2 = occ.addLine(p10, p11)
    l3 = occ.addLine(p11, p01)
    l4 = occ.addLine(p01, p00)
    wire = occ.addWire([l1, l2, l3, l4])
    surf = occ.addPlaneSurface([wire])

    # Extrude along hvector to create a volume
    out = occ.extrude([(2, surf)], hv[0], hv[1], hv[2])
    # Find the volume entity among the returned entities
    vol_tags = [tag for (dim, tag) in out if dim == 3]
    if not vol_tags:
        raise RuntimeError("Failed to create volume via extrusion")
    return vol_tags[0]


def _fragment_conductor_volumes(occ, volume_tags: List[int]) -> List[int]:
    """
    Run a single OCC fragment operation on the provided volumes to break
    overlapping regions into disjoint solids. Returns the resulting volume tags.
    If fragmentation fails, the original tags are returned.
    """
    if len(volume_tags) <= 1:
        return list(volume_tags)

    try:
        frag_out, _ = occ.fragment([(3, t) for t in volume_tags], [])
        occ.synchronize()
    except Exception as exc:
        raise RuntimeError(f"OCC fragment failed ({exc})")

    frag_vols = [tag for (dim, tag) in frag_out if dim == 3]
    if not frag_vols:
        return list(volume_tags)

    try:
        occ.removeAllDuplicates()
        occ.synchronize()
    except Exception:
        pass

    return frag_vols


def _robust_fuse_volumes(occ, volume_tags: List[int]) -> List[int]:
    """
    Fuse a list of volume tags by accumulating pairwise OCC fuse operations.
    If any fuse call fails, the offending piece is kept as-is so geometry is not lost.
    Returns the resulting volume tags (may be multiple if unions fail).
    """
    if len(volume_tags) <= 1:
        return list(volume_tags)

    acc: List[Tuple[int, int]] = [(3, volume_tags[0])]
    for tag in volume_tags[1:]:
        try:
            fuse_res, _ = occ.fuse(acc, [(3, tag)], removeObject=True, removeTool=True)
            occ.synchronize()
        except Exception:
            fuse_res = None

        if not fuse_res:
            acc = list(acc) + [(3, tag)]
            continue

        if isinstance(fuse_res, tuple):
            fuse_res = [fuse_res]

        fused_pairs = [(dim, t) for (dim, t) in fuse_res if dim == 3]
        if fused_pairs:
            acc = fused_pairs
        else:
            acc = list(acc) + [(3, tag)]

    try:
        occ.removeAllDuplicates()
        occ.synchronize()
    except Exception:
        pass

    return [t for (dim, t) in acc if dim == 3]


def build_geometry_gmsh(cap3d: Dict[str, List[Dict[str, Tuple[float, float, float]]]], unit_scale: float,
                        union: bool = True) -> Tuple[Dict[str, List[int]], Dict[str, List[int]], List[int]]:
    """
    Build OCC volumes per conductor from CAP3D blocks.

    Returns
    -------
    (volumes_per_cond, surfaces_per_cond, surfaces_to_reverse)
    - volumes_per_cond: dict mapping conductor name -> list of volume tags
    - surfaces_per_cond: dict mapping conductor name -> list of surface tags
    - surfaces_to_reverse: list of surface tags that need mesh reversal (originally inward-facing)
    """
    occ = gmsh.model.occ
    volumes_per_cond: Dict[str, List[int]] = {}

    skipped = 0
    union_failures = 0
    total_blocks = sum(len(blocks) for blocks in cap3d.values())
    pbar = tqdm(total=total_blocks, desc="Building geometry", unit="blk")
    for cond, blocks in cap3d.items():
        vol_tags: List[int] = []
        for blk in blocks:
            base = tuple(unit_scale * c for c in blk["basepoint"])  # type: ignore
            v1 = tuple(unit_scale * c for c in blk["v1"])  # type: ignore
            v2 = tuple(unit_scale * c for c in blk["v2"])  # type: ignore
            hv = tuple(unit_scale * c for c in blk["hvector"])  # type: ignore
            try:
                vol = add_volume_from_block(occ, base, v1, v2, hv)
                vol_tags.append(vol)
            except Exception as e:
                skipped += 1
                # Uncomment for debugging: print(f"Skipped block in {cond}: {e}", file=sys.stderr)
            finally:
                try:
                    pbar.update(1)
                except Exception:
                    pass

        if union and len(vol_tags) > 1:
            occ.synchronize()
            fragments = _fragment_conductor_volumes(occ, vol_tags)
            fused = _robust_fuse_volumes(occ, fragments)
            if fused:
                vol_tags = fused
            else:
                vol_tags = fragments

        volumes_per_cond[cond] = vol_tags

        try:
            occ.removeAllDuplicates()
        except Exception:
            pass
        occ.synchronize()

        if union and len(vol_tags) > 1:
            union_failures += 1

    occ.synchronize()
    try:
        pbar.close()
    except Exception:
        pass

    # Report skipped/failed blocks
    if skipped > 0:
        print(f"WARNING: Skipped {skipped} degenerate or invalid blocks")
    if union_failures > 0:
        print(f"WARNING: {union_failures} conductor(s) failed boolean union (overlapping surfaces may exist)")

    # Collect boundary surfaces per conductor
    # First, get all valid volume tags currently in the model
    valid_volumes = set(tag for (dim, tag) in gmsh.model.getEntities(dim=3))

    surfaces_per_cond: Dict[str, List[int]] = {}
    surfaces_to_reverse: List[int] = []  # Track surfaces that need mesh reversal
    for cond, vols in volumes_per_cond.items():
        # Filter to only valid volumes
        valid_vols = [v for v in vols if v in valid_volumes]
        if len(valid_vols) < len(vols):
            print(f"WARNING: Conductor '{cond}' has {len(vols) - len(valid_vols)} invalid volume tags (removed)")

        # Update volumes_per_cond to only include valid volumes
        volumes_per_cond[cond] = valid_vols

        # Warn if conductor has multiple volumes (indicates failed union = internal surfaces in output)
        if len(valid_vols) > 1:
            print(f"WARNING: Conductor '{cond}' has {len(valid_vols)} separate volumes!")

        if not valid_vols:
            surfaces_per_cond[cond] = []
            continue

        boundary = gmsh.model.getBoundary(
            [(3, vt) for vt in valid_vols],
            combined=True,
            oriented=True,  # Get signed tags for orientation
            recursive=False,
        )
        # With oriented=True: collect ALL boundary surfaces and their signs
        # According to gmsh docs, signed tags indicate orientation relative to parent volume
        signed_surfaces = [(dim, tag) for (dim, tag) in boundary if dim == 2]
        positive_tags = [abs(tag) for (dim, tag) in signed_surfaces if tag > 0]
        negative_tags = [abs(tag) for (dim, tag) in signed_surfaces if tag < 0]

        # Try reversing ALL surfaces
        inward_surfaces = set(negative_tags)
        surf_tags = sorted({abs(tag) for (dim, tag) in boundary if dim == 2})

        cond_vol_set = set(valid_vols)
        filtered_surfaces: List[int] = []
        removed_internal = 0

        for surf_tag in surf_tags:
            try:
                adj_dims, adj_tags = gmsh.model.getAdjacencies(2, surf_tag)
            except Exception:
                adj_dims, adj_tags = (), ()

            # Count adjacent conductor volumes
            conductor_adj = 0
            for d, t in zip(adj_dims, adj_tags):
                if d == 3 and t in cond_vol_set:
                    conductor_adj += 1

            if conductor_adj <= 1:
                filtered_surfaces.append(surf_tag)
            else:
                removed_internal += 1

        surfaces_per_cond[cond] = filtered_surfaces
    return volumes_per_cond, surfaces_per_cond, surfaces_to_reverse


def setup_adaptive_triangle_mesh(lc_min: float, lc_max: float,
                                 dist_min: float, dist_max: float) -> None:
    """
    Configure Gmsh for triangular surface mesh with edge-distance adaptivity.
    """

    gmsh.option.setNumber("Mesh.RecombineAll", 0)
    gmsh.option.setNumber("Mesh.Algorithm", 6)

    # Base characteristic lengths
    for key, val in (
        ("Mesh.CharacteristicLengthMin", lc_min),
        ("Mesh.CharacteristicLengthMax", lc_max),
        ("Mesh.CharacteristicLengthFromCurvature", 1),
        ("Mesh.CharacteristicLengthExtendFromBoundary", 1),
    ):
        try:
            gmsh.option.setNumber(key, val)
        except Exception:
            pass

    # Build a distance field from all curves (model edges)
    curves = [tag for (dim, tag) in gmsh.model.getEntities(dim=1)]
    if curves:
        fdist = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(fdist, "CurvesList", curves)
        gmsh.model.mesh.field.setNumber(fdist, "Sampling", 100)

        fthr = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(fthr, "InField", fdist)
        gmsh.model.mesh.field.setNumber(fthr, "SizeMin", lc_min)
        gmsh.model.mesh.field.setNumber(fthr, "SizeMax", lc_max)
        gmsh.model.mesh.field.setNumber(fthr, "DistMin", dist_min)
        gmsh.model.mesh.field.setNumber(fthr, "DistMax", dist_max)
        gmsh.model.mesh.field.setAsBackgroundMesh(fthr)


def add_normal_visualization(node_coords: Dict[int, Tuple[float, float, float]], scale_factor: float = 1.0) -> None:
    """Add triangle normal vectors to Gmsh view for visualization.

    Parameters
    ----------
    node_coords : dict
        Mapping from node tag to (x, y, z) coordinates
    scale_factor : float
        Scale factor for normal vector length (relative to average edge length)
    """

    # Collect all triangles from all surfaces
    triangle_data = []
    for (dim, tag) in gmsh.model.getEntities(dim=2):
        types, elemTags, elemNodeTags = gmsh.model.mesh.getElements(2, tag)
        for t, nodeList in zip(types, elemNodeTags):
            if t != 2:  # only triangles
                continue
            # nodeList is flat: [n1,n2,n3, n1,n2,n3, ...]
            for i in range(0, len(nodeList), 3):
                n1 = int(nodeList[i])
                n2 = int(nodeList[i+1])
                n3 = int(nodeList[i+2])
                triangle_data.append((n1, n2, n3))

    # Compute normals and average edge length
    edge_lengths = []
    normal_vectors = []
    centroids = []

    for (n1, n2, n3) in triangle_data:
        p1 = node_coords[n1]
        p2 = node_coords[n2]
        p3 = node_coords[n3]

        # Compute centroid
        cx = (p1[0] + p2[0] + p3[0]) / 3.0
        cy = (p1[1] + p2[1] + p3[1]) / 3.0
        cz = (p1[2] + p2[2] + p3[2]) / 3.0

        # Compute edge vectors
        e1 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
        e2 = (p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2])

        # Edge lengths for scaling
        edge_lengths.append(math.sqrt(e1[0]**2 + e1[1]**2 + e1[2]**2))
        edge_lengths.append(math.sqrt(e2[0]**2 + e2[1]**2 + e2[2]**2))

        # Compute normal via cross product: e1 × e2
        nx = e1[1]*e2[2] - e1[2]*e2[1]
        ny = e1[2]*e2[0] - e1[0]*e2[2]
        nz = e1[0]*e2[1] - e1[1]*e2[0]

        # Normalize
        norm = math.sqrt(nx*nx + ny*ny + nz*nz)
        if norm > 1e-12:
            nx /= norm
            ny /= norm
            nz /= norm

        centroids.append((cx, cy, cz))
        normal_vectors.append((nx, ny, nz))

    # Compute automatic scale based on average edge length
    avg_edge = sum(edge_lengths) / max(len(edge_lengths), 1)
    arrow_length = avg_edge * scale_factor

    # Create a post-processing view with vector data
    # View format: list-based vectors (VL)
    # Each vector: x, y, z, vx, vy, vz
    view_tag = gmsh.view.add("Triangle Normals")

    # Build data string for gmsh.view.addListData
    # Format: "VL" (vector line) with points and vectors
    data = []
    for (cx, cy, cz), (nx, ny, nz) in zip(centroids, normal_vectors):
        # Start point
        data.extend([cx, cy, cz])
        # Vector components scaled
        data.extend([nx * arrow_length, ny * arrow_length, nz * arrow_length])

    # Add data to view (3D vectors)
    gmsh.view.addListData(view_tag, "VP", len(centroids), data)

    # Configure view options for better visualization
    gmsh.option.setNumber(f"View[{view_tag}].ShowScale", 0)  # Hide scale bar
    gmsh.option.setNumber(f"View[{view_tag}].VectorType", 5)  # Arrow3D
    gmsh.option.setNumber(f"View[{view_tag}].GlyphLocation", 1)  # COG (center of gravity)
    gmsh.option.setNumber(f"View[{view_tag}].ArrowSizeMin", 5)  # Minimum arrow head size
    gmsh.option.setNumber(f"View[{view_tag}].ArrowSizeMax", 20)  # Maximum arrow head size
    gmsh.option.setNumber(f"View[{view_tag}].LineWidth", 2)  # Arrow line width

def stream_write_qui(
    qui_path: str,
    group_entities: Dict[int, List[int]],
    node_coords_nm: Dict[int, Tuple[float, float, float]],
    group_names: Dict[int, str],
    base_label: str,
    flush_every: int = 50000,
) -> int:
    """Stream-write a FasterCap/FASTCAP .qui file with triangles.

    - Iterates groups and their surfaces; writes triangles incrementally.
    - Preserves group (net) names.
    - Returns total triangle count written.
    """
    NM_TO_M = 1
    total = 0
    with open(qui_path, 'w', buffering=1024 * 1024) as f:
        f.write(f"0 {base_label}\n")
        # Sort groups by name for stable ordering
        for pg in sorted(group_entities.keys(), key=lambda t: group_names.get(t, str(t))):
            label = group_names.get(pg, f"COND_{pg}")
            for surf in group_entities[pg]:
                types, elemTags, elemNodeTags = gmsh.model.mesh.getElements(2, surf)
                for t, nodeList in zip(types, elemNodeTags):
                    if t != 2:  # only triangles
                        continue
                    # nodeList is flat: [n1,n2,n3, n1,n2,n3, ...]
                    for i in range(0, len(nodeList), 3):
                        n1 = int(nodeList[i]); n2 = int(nodeList[i+1]); n3 = int(nodeList[i+2])
                        x1, y1, z1 = node_coords_nm[n1]
                        x2, y2, z2 = node_coords_nm[n2]
                        x3, y3, z3 = node_coords_nm[n3]
                        f.write(
                            f"T {label} {x1*NM_TO_M:.6g} {y1*NM_TO_M:.6g} {z1*NM_TO_M:.6g} "
                            f"{x2*NM_TO_M:.6g} {y2*NM_TO_M:.6g} {z2*NM_TO_M:.6g} "
                            f"{x3*NM_TO_M:.6g} {y3*NM_TO_M:.6g} {z3*NM_TO_M:.6g}\n"
                        )
                        total += 1
                        if flush_every and (total % flush_every == 0):
                            f.flush()
    return total


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    input_path = args.input

    # Assume CAP3D units are micrometers; work internally in nanometers (1 nm = 1 unit)
    unit_scale = 1e3

    # Parse CAP3D
    cap = parse_cap3d(input_path)

    gmsh.initialize()
    gmsh.model.add("cap3d")
    try:
        # Silence Gmsh info/progress output (avoid "Meshing curve ..." spam)
        try:
            gmsh.option.setNumber("General.Verbosity", 0)
        except Exception:
            pass
        for opt, val in (("General.Terminal", 0), ("General.ProgressMeter", 0)):
            try:
                gmsh.option.setNumber(opt, val)
            except Exception:
                pass

        # Set OCC tolerances for robust boolean operations on nanometer-scale geometry
        # Default tolerances (1e-8) are too strict for nm units; use more forgiving values
        for opt, val in (
            ("Geometry.Tolerance", 1e-5),                # General geometry tolerance (nm units)
            ("Geometry.ToleranceBoolean", 1e-5),         # Boolean operation tolerance
            ("Geometry.OCCAutoFix", 1),                  # Enable automatic fixing
            ("Geometry.OCCFixDegenerated", 1),           # Fix degenerate entities
            ("Geometry.OCCFixSmallEdges", 1),            # Merge small edges
            ("Geometry.OCCFixSmallFaces", 1),            # Merge small faces
            ("Geometry.OCCSewFaces", 2),                 # Aggressive sewing of adjacent faces
            ("Geometry.MatchGeomAndMesh", 0),            # Allow geometry/mesh mismatch
        ):
            try:
                gmsh.option.setNumber(opt, val)
            except Exception:
                pass

        # Build geometry and collect per-conductor surfaces (union to remove internals)
        do_union = not args.no_union
        volumes_per_cond, surfaces_per_cond, surfaces_to_reverse = build_geometry_gmsh(cap, unit_scale=unit_scale, union=do_union)

        # Add Physical Groups for surfaces per conductor
        for idx, cond in enumerate(sorted(surfaces_per_cond.keys()), start=1):
            surf_tags = surfaces_per_cond[cond]
            if not surf_tags:
                continue
            pg = gmsh.model.addPhysicalGroup(2, surf_tags, tag=idx)
            gmsh.model.setPhysicalName(2, pg, f"cond:{cond}")

        # Derive automatic mesh sizes from model bbox (in nm units)
        # Compute global bbox from all surfaces
        xmins, ymins, zmins, xmaxs, ymaxs, zmaxs = [], [], [], [], [], []
        for (dim, tag) in gmsh.model.getEntities(dim=2):
            (xmin, ymin, zmin, xmax, ymax, zmax) = gmsh.model.getBoundingBox(dim, tag)
            xmins.append(xmin); ymins.append(ymin); zmins.append(zmin)
            xmaxs.append(xmax); ymaxs.append(ymax); zmaxs.append(zmax)
        if not xmins:
            raise RuntimeError("No surfaces found to mesh")
        Lx = max(xmaxs) - min(xmins)
        Ly = max(ymaxs) - min(ymins)
        Lz = max(zmaxs) - min(zmins)
        Lmin = max(1e-12, min(Lx, Ly, Lz))
        diag = math.sqrt(Lx*Lx + Ly*Ly + Lz*Lz)
        # Heuristic sizes with user-adjustable diagonal divisor (nm units)
        auto_lc_max = diag / args.diag_divisor
        lc_max = max(auto_lc_max, 1.0)
        lc_min = max(lc_max / 5.0, 1.0)  # ensure at least 1 nm

        dist_min = lc_max
        dist_max = 10.0 * lc_max

        # Mesh settings (triangles + adaptive)
        setup_adaptive_triangle_mesh(lc_min=lc_min, lc_max=lc_max,
                                     dist_min=dist_min, dist_max=dist_max)

        # Generate 2D mesh on all boundary surfaces
        gmsh.model.mesh.generate(2)

        # Output
        base, _ = os.path.splitext(input_path)
        out_path = f"{base}.msh"
        # Write with a short progress indicator
        with tqdm(total=1, desc="Writing mesh", unit="file") as pbar:
            gmsh.write(out_path)
            pbar.update(1)

        # Summarize triangle count and write QUI with preserved net names
        # Build node coordinate map (in nm)
        node_tags_np, node_coords_np, _ = gmsh.model.mesh.getNodes()
        node_tags = node_tags_np.tolist() if hasattr(node_tags_np, 'tolist') else list(node_tags_np)
        if hasattr(node_coords_np, 'reshape'):
            coords_arr = node_coords_np.reshape((-1, 3))
            coords_iter = [(float(x), float(y), float(z)) for (x, y, z) in coords_arr]
        else:
            coords_iter = []
            for i in range(0, len(node_coords_np), 3):
                coords_iter.append((float(node_coords_np[i]), float(node_coords_np[i+1]), float(node_coords_np[i+2])))
        node_dict = {int(tag): coords_iter[idx] for idx, tag in enumerate(node_tags)}

        # Map physical groups to their surface entities; preserve names
        group_names: Dict[int, str] = {}
        group_entities: Dict[int, List[int]] = {}
        for (dim, pg) in gmsh.model.getPhysicalGroups(2):
            name = gmsh.model.getPhysicalName(2, pg) or f"COND_{pg}"
            # Strip a leading "cond:" if present to preserve clean net name
            if name.startswith("cond:"):
                name = name[5:]
            group_names[pg] = name
            entities = gmsh.model.getEntitiesForPhysicalGroup(2, pg)
            # Ensure list-like and not ambiguous truth value (numpy)
            entities_list = entities.tolist() if hasattr(entities, 'tolist') else list(entities)
            if len(entities_list) > 0:
                group_entities[pg] = entities_list

        qui_path = f"{base}.qui"
        total_tris = stream_write_qui(
            qui_path,
            group_entities,
            node_dict,
            group_names,
            base_label=os.path.basename(base),
            flush_every=50000,
        )

        # Validate conductor counts
        cap3d_conductor_count = len(cap)
        qui_conductor_count = len(group_names)

        if cap3d_conductor_count != qui_conductor_count:
            print(f"  ✗ WARNING: Conductor count mismatch! Difference: {qui_conductor_count - cap3d_conductor_count}")

        # Also verify by parsing the QUI file to count unique conductor labels
        qui_labels = set()
        with open(qui_path, 'r') as f:
            for line in f:
                if line.startswith('T '):
                    parts = line.split()
                    if len(parts) >= 2:
                        qui_labels.add(parts[1])

        qui_actual_count = len(qui_labels)

        if qui_actual_count != cap3d_conductor_count:
            # Show which conductors differ
            cap3d_names = set(cap.keys())
            qui_names = qui_labels

            missing_in_qui = cap3d_names - qui_names
            extra_in_qui = qui_names - cap3d_names

            if missing_in_qui:
                print(f"  Conductors in CAP3D but not in QUI: {sorted(missing_in_qui)}")
            if extra_in_qui:
                print(f"  Conductors in QUI but not in CAP3D: {sorted(extra_in_qui)}")

        # Add normal vectors to view before launching GUI (if requested)
        if args.show_normals:
            add_normal_visualization(node_dict, scale_factor=args.normal_scale)

        # Launch interactive viewer for inspection (if available)
        gmsh.fltk.run()

    finally:
        gmsh.finalize()
