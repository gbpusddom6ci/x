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


@dataclass
class PatternBranch:
    """Represents a single pattern branch being explored."""
    path: List[int]  # Sequence of offsets in this branch
    file_indices: List[int]  # Which file index provided each offset
    current_state: str  # 'reset', 'plus_started', 'minus_started', 'complete'
    expected_next: Set[int]  # Valid next offsets for this branch


@dataclass
class PatternResult:
    """Final pattern result with completion status."""
    pattern: List[int]  # The complete pattern sequence
    file_sequence: List[Tuple[int, str]]  # [(file_idx, filename), ...]
    is_complete: bool  # Whether pattern ends with 0
    length: int  # Number of offsets in pattern


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
    
    # First file must contain at least one starting point
    for offset in first_offsets:
        if offset == 0:
            # Start with 0 - can branch to ±1 or ±3 next
            initial_branches.append(PatternBranch(
                path=[0],
                file_indices=[0],
                current_state='reset',
                expected_next={-3, -1, 1, 3}
            ))
        elif offset in {-3, -1, 1, 3}:
            # Start directly without 0 (valid for first position)
            state = 'plus_started' if offset > 0 else 'minus_started'
            expected = _get_expected_next(offset, state)
            initial_branches.append(PatternBranch(
                path=[offset],
                file_indices=[0],
                current_state=state,
                expected_next=expected
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
                    new_expected = _get_expected_next(offset, new_state)
                    
                    new_branch = PatternBranch(
                        path=new_path,
                        file_indices=new_file_indices,
                        current_state=new_state,
                        expected_next=new_expected
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
            length=len(branch.path)
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


def _get_expected_next(current_offset: int, current_state: str) -> Set[int]:
    """Get valid next offsets based on current offset and state."""
    if current_state == 'reset':
        # After 0, can start with ±1 or ±3
        return {-3, -1, 1, 3}
    
    if current_offset == 0:
        # Just hit 0, can start new cycle
        return {-3, -1, 1, 3}
    
    # In middle of cycle - determine next step
    if current_state == 'plus_started':
        # Positive cycle: can go +1→+2→+3 or +3→+2→+1
        if current_offset == 1:
            return {2}  # +1 → +2
        elif current_offset == 2:
            return {1, 3}  # +2 → +1 (reverse) or +3 (forward)
        elif current_offset == 3:
            return {2, 0}  # +3 → +2 (continue reverse) or 0 (end)
        else:
            return set()
    
    elif current_state == 'minus_started':
        # Negative cycle: can go -1→-2→-3 or -3→-2→-1
        if current_offset == -1:
            return {-2}  # -1 → -2
        elif current_offset == -2:
            return {-1, -3}  # -2 → -1 (reverse) or -3 (forward)
        elif current_offset == -3:
            return {-2, 0}  # -3 → -2 (continue reverse) or 0 (end)
        else:
            return set()
    
    return set()


def format_pattern_results(results: List[PatternResult]) -> str:
    """
    Format pattern results for HTML display.
    
    Returns HTML string with pattern analysis summary.
    """
    if not results:
        return "<p><strong>❌ Pattern bulunamadı</strong> - Geçerli örüntü oluşturulamadı.</p>"
    
    html_parts = [f"<p><strong>✅ {len(results)} geçerli pattern bulundu:</strong></p>"]
    html_parts.append("<ol>")
    
    for idx, result in enumerate(results, 1):
        # Format pattern sequence
        pattern_str = " → ".join([
            f"{o:+d}" if o != 0 else "0" for o in result.pattern
        ])
        
        # Format file sequence
        file_str = ", ".join([
            f"Dosya {file_idx}: {filename}" for file_idx, filename in result.file_sequence
        ])
        
        # Completion status
        status = "✅ Tamamlandı" if result.is_complete else "⚠️ Devam ediyor"
        
        html_parts.append(f"""
        <li>
            <strong>Pattern {idx}:</strong> <code>{pattern_str}</code> 
            <span style="color: {'green' if result.is_complete else 'orange'};">({status})</span>
            <br>
            <small style="color: #666;">{file_str}</small>
        </li>
        """)
    
    html_parts.append("</ol>")
    
    return "".join(html_parts)
