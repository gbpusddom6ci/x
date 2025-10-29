"""
Pattern Analysis for XYZ Offset Sequences

Analyzes multiple XYZ offset sets to find valid patterns.

Pattern Rules:
1. Each 0 acts as a reset point
2. After each 0, can start with ±1 or ±3
3. Once a sign is chosen, the triplet continues with that sign
4. Valid triplets: +1→+2→+3, +3→+2→+1, -1→-2→-3, -3→-2→-1
5. No gaps allowed (1→3 invalid)
6. After triplet completion, must have 0 to reset
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass

MINUTES_PER_STEP = 48


@dataclass
class PatternBranch:
    """Represents a single pattern branch being explored."""
    path: List[int]  # Sequence of offsets in this branch
    file_indices: List[int]  # Which file index provided each offset
    current_state: str  # 'reset', 'plus_started', 'minus_started', 'complete'
    expected_next: Set[int]  # Valid next offsets for this branch
    direction: Optional[str]  # 'ascending' (1→2→3), 'descending' (3→2→1), or None


@dataclass
class PatternResult:
    """Final pattern result with completion status."""
    pattern: List[int]  # The complete pattern sequence
    file_sequence: List[Tuple[int, str]]  # [(file_idx, filename), ...]
    is_complete: bool  # Whether pattern ends with 0
    length: int  # Number of offsets in pattern
    expected_next: Set[int]  # Valid next offsets for continuation


def find_valid_patterns(
    xyz_data: List[Tuple[str, List[int]]],  # [(filename, xyz_offsets), ...]
    max_branches: int = 1000,
) -> List[PatternResult]:
    """
    Find all valid patterns from multiple XYZ offset sets.
    
    Args:
        xyz_data: List of (filename, xyz_offsets) tuples
        max_branches: Maximum number of branches to explore (prevents explosion)
    
    Returns:
        List of valid PatternResult objects
    """
    if not xyz_data:
        return []
    
    # Initialize: start from first file's offsets
    initial_branches: List[PatternBranch] = []
    first_filename, first_offsets = xyz_data[0]
    
    # First file can start with ANY offset (data before is unknown)
    for offset in first_offsets:
        if offset == 0:
            # Start with 0 - can branch to ±1 or ±3 next
            initial_branches.append(PatternBranch(
                path=[0],
                file_indices=[0],
                current_state='reset',
                expected_next={-3, -1, 1, 3},
                direction=None
            ))
        elif offset in {-3, -1, 1, 3}:
            # Start with ±1 or ±3: single direction known
            state = 'plus_started' if offset > 0 else 'minus_started'
            direction = 'ascending' if offset in {1, -1} else 'descending'
            expected = _get_expected_next(offset, state, direction)
            initial_branches.append(PatternBranch(
                path=[offset],
                file_indices=[0],
                current_state=state,
                expected_next=expected,
                direction=direction
            ))
        elif offset in {-2, 2}:
            # Start with ±2: direction unknown, try both
            state = 'plus_started' if offset > 0 else 'minus_started'
            
            # Branch 1: Ascending (±1 → ±2 → ±3)
            initial_branches.append(PatternBranch(
                path=[offset],
                file_indices=[0],
                current_state=state,
                expected_next={3 if offset > 0 else -3},
                direction='ascending'
            ))
            
            # Branch 2: Descending (±3 → ±2 → ±1)
            initial_branches.append(PatternBranch(
                path=[offset],
                file_indices=[0],
                current_state=state,
                expected_next={1 if offset > 0 else -1},
                direction='descending'
            ))
    
    if not initial_branches:
        return []
    
    # Explore all branches through remaining files
    active_branches = initial_branches
    completed_patterns: List[PatternResult] = []
    
    for file_idx in range(1, len(xyz_data)):
        filename, offsets = xyz_data[file_idx]
        new_branches: List[PatternBranch] = []
        
        for branch in active_branches:
            # Try each offset from current file
            for offset in offsets:
                # Check if this offset is valid for current branch
                if offset in branch.expected_next:
                    # Create new branch with this offset
                    new_path = branch.path + [offset]
                    new_file_indices = branch.file_indices + [file_idx]
                    new_state = _get_next_state(branch.current_state, offset)
                    
                    # Determine direction: set on first non-zero in cycle, reset on 0
                    new_direction = branch.direction
                    if offset == 0:
                        new_direction = None  # Reset direction on 0
                    elif branch.current_state == 'reset' and offset != 0:
                        # First step after 0: set direction
                        new_direction = 'ascending' if offset in {1, -1} else 'descending'
                    
                    new_expected = _get_expected_next(offset, new_state, new_direction)
                    
                    new_branch = PatternBranch(
                        path=new_path,
                        file_indices=new_file_indices,
                        current_state=new_state,
                        expected_next=new_expected,
                        direction=new_direction
                    )
                    new_branches.append(new_branch)
                    
                    # Branch limit check
                    if len(new_branches) >= max_branches:
                        break
            
            if len(new_branches) >= max_branches:
                break
        
        active_branches = new_branches
        
        if not active_branches:
            break
    
    # Convert final branches to results
    for branch in active_branches:
        # Check if pattern is complete (ends with 0)
        is_complete = (branch.path[-1] == 0 if branch.path else False)
        
        # Build file sequence
        file_sequence = []
        for i, file_idx in enumerate(branch.file_indices):
            filename = xyz_data[file_idx][0]
            file_sequence.append((file_idx + 1, filename))  # 1-indexed for display
        
        result = PatternResult(
            pattern=branch.path,
            file_sequence=file_sequence,
            is_complete=is_complete,
            length=len(branch.path),
            expected_next=branch.expected_next
        )
        completed_patterns.append(result)
    
    # Sort by completion status (complete first) and length (longer first)
    completed_patterns.sort(key=lambda x: (not x.is_complete, -x.length))
    
    return completed_patterns


def _get_next_state(current_state: str, offset: int) -> str:
    """Determine next state based on current state and offset."""
    if offset == 0:
        return 'reset'
    elif current_state == 'reset':
        return 'plus_started' if offset > 0 else 'minus_started'
    else:
        return current_state


def _get_expected_next(current_offset: int, current_state: str, direction: Optional[str]) -> Set[int]:
    """Get valid next offsets based on current offset, state, and direction."""
    if current_state == 'reset':
        # After 0, can start with ±1 or ±3
        return {-3, -1, 1, 3}
    
    if current_offset == 0:
        # Just hit 0, can start new cycle
        return {-3, -1, 1, 3}
    
    # In middle of cycle - MUST follow direction
    if current_state == 'plus_started':
        if direction == 'ascending':
            # +1 → +2 → +3 → 0
            if current_offset == 1:
                return {2}
            elif current_offset == 2:
                return {3}
            elif current_offset == 3:
                return {0}
        elif direction == 'descending':
            # +3 → +2 → +1 → 0
            if current_offset == 3:
                return {2}
            elif current_offset == 2:
                return {1}
            elif current_offset == 1:
                return {0}
    
    elif current_state == 'minus_started':
        if direction == 'ascending':
            # -1 → -2 → -3 → 0
            if current_offset == -1:
                return {-2}
            elif current_offset == -2:
                return {-3}
            elif current_offset == -3:
                return {0}
        elif direction == 'descending':
            # -3 → -2 → -1 → 0
            if current_offset == -3:
                return {-2}
            elif current_offset == -2:
                return {-1}
            elif current_offset == -1:
                return {0}
    
    return set()


def format_pattern_results(results: List[PatternResult]) -> str:
    """
    Format pattern results for HTML display.
    
    Returns HTML string with pattern analysis summary.
    """
    if not results:
        return "<p><strong>❌ Pattern bulunamadı</strong> - Geçerli örüntü oluşturulamadı.</p>"
    
    # Build color map for groups (2-3 consecutive non-zero offsets)
    # Skip 0s, group consecutive offsets (doublets or triplets), assign same color
    group_map = {}  # (file1, file2, [file3], offset1, offset2, [offset3]) -> color
    group_counter = 0
    
    # Predefined color palette (pastel colors for better readability)
    colors = [
        '#FFE5E5', '#E5F3FF', '#E5FFE5', '#FFF5E5', '#FFE5F5', '#F5E5FF',
        '#E5FFFF', '#FFFFE5', '#F0E5FF', '#E5FFF0', '#FFE5EB', '#E5F0FF',
        '#F5FFE5', '#FFE5F0', '#E5FFE8', '#FFF0E5', '#E5E5FF', '#FFFFE8',
        '#FFE8E5', '#E5FFFA', '#FAE5FF', '#E5FAFF', '#FFEFA5', '#E5FFEF',
    ]
    
    # Build group map (supports doublets and triplets)
    for result in results:
        i = 0
        while i < len(result.pattern):
            # Skip 0s
            if result.pattern[i] == 0:
                i += 1
                continue
            
            # Collect group (2-3 consecutive non-zero offsets)
            group_offsets = []
            group_files = []
            j = i
            while j < len(result.pattern) and len(group_offsets) < 3:
                if result.pattern[j] == 0:
                    break
                group_offsets.append(result.pattern[j])
                if j < len(result.file_sequence):
                    _, filename = result.file_sequence[j]
                    group_files.append(filename)
                j += 1
            
            # If we have a complete group (2 or 3 offsets), create a key
            if len(group_offsets) >= 2 and len(group_files) >= 2:
                group_key = tuple(group_files + group_offsets)
                if group_key not in group_map:
                    group_map[group_key] = colors[group_counter % len(colors)]
                    group_counter += 1
            
            i = j if j > i else i + 1
    
    html_parts = [f"<p><strong>✅ {len(results)} geçerli pattern bulundu:</strong></p>"]
    html_parts.append("<ol>")
    
    for idx, result in enumerate(results, 1):
        # Build pattern string with hover tooltips and group-based color coding
        pattern_parts = []
        
        # Build group membership for this pattern
        offset_to_color = {}  # offset_index -> color
        i = 0
        while i < len(result.pattern):
            # Skip 0s
            if result.pattern[i] == 0:
                i += 1
                continue
            
            # Collect group (2-3 offsets)
            group_offsets = []
            group_files = []
            group_indices = []
            j = i
            while j < len(result.pattern) and len(group_offsets) < 3:
                if result.pattern[j] == 0:
                    break
                group_offsets.append(result.pattern[j])
                group_indices.append(j)
                if j < len(result.file_sequence):
                    _, filename = result.file_sequence[j]
                    group_files.append(filename)
                j += 1
            
            # If complete group (2 or 3), assign color to all offsets
            if len(group_offsets) >= 2 and len(group_files) >= 2:
                group_key = tuple(group_files + group_offsets)
                color = group_map.get(group_key, 'transparent')
                for gi in group_indices:
                    offset_to_color[gi] = color
            
            i = j if j > i else i + 1
        
        # Now build the pattern string with continuous group blocks
        i = 0
        while i < len(result.pattern):
            offset = result.pattern[i]
            offset_str = f"{offset:+d}" if offset != 0 else "0"
            
            # Check if this is start of a colored triplet
            if i in offset_to_color and offset != 0:
                # Find the triplet boundaries
                triplet_start = i
                triplet_color = offset_to_color[i]
                triplet_end = i
                
                # Find where this triplet ends (same color)
                while triplet_end < len(result.pattern) and offset_to_color.get(triplet_end) == triplet_color:
                    triplet_end += 1
                
                # Build continuous triplet block
                triplet_parts = []
                for j in range(triplet_start, triplet_end):
                    o = result.pattern[j]
                    o_str = f"{o:+d}" if o != 0 else "0"
                    
                    # Get filename for tooltip
                    if j < len(result.file_sequence):
                        _, full_filename = result.file_sequence[j]
                        filename = full_filename.rsplit('.', 1)[0] if '.' in full_filename else full_filename
                        triplet_parts.append(f'<span title="{filename}" style="cursor:help;">{o_str}</span>')
                    else:
                        triplet_parts.append(o_str)
                
                # Wrap entire triplet in colored block
                triplet_html = ' → '.join(triplet_parts)
                pattern_parts.append(
                    f'<span style="'
                    f'background-color:{triplet_color}; padding:4px 8px; border-radius:4px; '
                    f'display:inline-block; margin:0 4px;'
                    f'">{triplet_html}</span>'
                )
                
                i = triplet_end
            else:
                # Single offset (0 or not in triplet)
                if i < len(result.file_sequence):
                    _, full_filename = result.file_sequence[i]
                    filename = full_filename.rsplit('.', 1)[0] if '.' in full_filename else full_filename
                    pattern_parts.append(
                        f'<span title="{filename}" style="cursor:help; border-bottom:1px dotted #999;">{offset_str}</span>'
                    )
                else:
                    pattern_parts.append(offset_str)
                i += 1
        
        pattern_str = " → ".join(pattern_parts)
        
        # Format expected next offsets
        if result.expected_next:
            next_offsets = sorted(result.expected_next)
            next_str = ", ".join([f"{o:+d}" if o != 0 else "0" for o in next_offsets])
            status_html = f'<span style="color: {"green" if result.is_complete else "orange"};">(→ next: {next_str})</span>'
        else:
            status_html = '<span style="color: gray;">(→ next: none)</span>'
        
        html_parts.append(f"""
        <li>
            <strong>Pattern {idx}:</strong> <code style="font-size:14px;">{pattern_str}</code> {status_html}
        </li>
        """)
    
    html_parts.append("</ol>")
    
    return "".join(html_parts)
