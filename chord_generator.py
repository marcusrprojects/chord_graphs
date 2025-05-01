# chord_generator.py

import itertools
import argparse
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages
import logging
import re # Import regex module for sanitizing filenames

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Core Chord Logic ---
def generate_chord_structure(root, chord_type, inversion=0):
    """
    Generates the notes and structure for a given musical chord.

    Args:
        root (str): The root note of the chord (e.g., "C", "G#").
        chord_type (str): The type of chord (e.g., "major", "minor", "7", "minor7", "maj7").
        inversion (int): The inversion number (0 for root position, 1 for first inversion, etc.).

    Returns:
        tuple: A tuple containing:
            - list[str]: Names of the notes in the chord.
            - list[str]: Key types ("white" or "black") for each note.
            - str: A title string for the chord diagram.

    Raises:
        ValueError: If the chord_type is unsupported or the root note is invalid.
    """
    intervals = {
        "major": [0, 4, 7],
        "minor": [0, 3, 7],
        "7": [0, 4, 7, 10],
        "minor7": [0, 3, 7, 10],
        "maj7": [0, 4, 7, 11],
    }

    chromatic_scale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    key_types = ["white", "black", "white", "black", "white", "white", "black", "white", "black", "white", "black", "white"]

    if chord_type not in intervals:
        raise ValueError(f"Unsupported chord type: {chord_type}")
    if root not in chromatic_scale:
         raise ValueError(f"Invalid root note: {root}")

    chord_intervals = intervals[chord_type][:] # Make a copy to avoid modifying original

    # Apply inversion
    num_notes = len(chord_intervals)
    # Ensure inversion is valid for the number of notes (e.g., inversion 3 doesn't exist for a triad)
    if inversion >= num_notes:
         raise ValueError(f"Inversion {inversion} is invalid for a {num_notes}-note chord ({chord_type})")

    actual_inversion = inversion # No modulo needed if we validate first

    for _ in range(actual_inversion):
         # Pop lowest note and add 12 semitones (octave up)
        chord_intervals.append(chord_intervals.pop(0) + 12)
    chord_intervals.sort() # Keep intervals sorted for consistent note order

    root_index = chromatic_scale.index(root)
    chord_notes_indices = [(root_index + interval) % 12 for interval in chord_intervals]
    chord_note_names = [chromatic_scale[note_index] for note_index in chord_notes_indices]
    key_colors = [key_types[note_index] for note_index in chord_notes_indices]

    inversion_str = f"(Inversion {actual_inversion})" if actual_inversion > 0 else "(Root Position)"
    title = f"{root} {chord_type} {inversion_str}"

    return chord_note_names, key_colors, title


def plot_chord_diagram(chord_note_names, key_colors, title):
    """
    Plots the chord diagram using Matplotlib and NetworkX.

    Args:
        chord_note_names (list[str]): Names of the notes in the chord.
        key_colors (list[str]): Key types ("white" or "black") for each note.
        title (str): The title for the plot.
    """
    graph = nx.Graph()
    positions = {}
    node_colors_map = []

    for i, note in enumerate(chord_note_names):
        key_color_value = (.2, .2, .2) if key_colors[i] == "black" else "whitesmoke"
        text_color = "white" if key_colors[i] == "black" else "black"
        # Ensure unique node names if duplicates exist (e.g., in inversions)
        node_id = f"{note}_{i}"
        graph.add_node(node_id, label=note, color=key_color_value, text_color=text_color)
        node_colors_map.append(key_color_value)
        # Position black keys slightly higher
        positions[node_id] = (i, 0.1 if key_colors[i] == "black" else 0)

    # Connect the notes (visually, not necessarily musically adjacent)
    node_ids = list(graph.nodes())
    for i in range(len(node_ids) - 1):
        graph.add_edge(node_ids[i], node_ids[i+1])

    # Create a new figure for each plot
    plt.figure(figsize=(8, 4)) # Adjusted figure size
    nx.draw(
        graph,
        pos=positions,
        with_labels=False,
        node_size=2500,
        node_color=node_colors_map,
        edge_color="gray",
        width=1.5,
    )

    # Add labels with appropriate text colors
    for node_id, (x, y) in positions.items():
        node_attr = graph.nodes[node_id]
        plt.text(
            x, y, node_attr['label'],
            fontsize=14,
            fontweight='bold',
            ha="center",
            va="center",
            color=node_attr['text_color']
        )

    plt.title(title, color="gray", fontsize=20, pad=20)
    plt.tight_layout()

    current_ylim = plt.ylim()
    # Add a buffer to the top and bottom limits
    plt.ylim(current_ylim[0] - 0.1, current_ylim[1] + 0.1)
    plt.axis("off") # Turn off axis AFTER adjusting limits

def generate_filename(args):
    """Generates a descriptive filename based on arguments."""

    # Define defaults for comparison
    default_roots = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    default_types = ["major", "minor", "7", "minor7", "maj7"]
    default_inversions = [0, 1, 2, 3]

    # Roots part
    if set(args.roots) == set(default_roots):
        roots_part = "Roots_All"
    elif len(args.roots) == 1:
        roots_part = f"Root_{args.roots[0]}"
    else:
        # Limit length if many specific roots are given
        roots_str = "-".join(args.roots)
        if len(roots_str) > 20:
             roots_part = f"Roots_{len(args.roots)}Custom"
        else:
             roots_part = f"Roots_{roots_str}"

    # Types part
    if set(args.types) == set(default_types):
        types_part = "Types_All"
    elif len(args.types) == 1:
        types_part = f"Type_{args.types[0]}"
    else:
        types_str = "-".join(args.types)
        if len(types_str) > 20:
             types_part = f"Types_{len(args.types)}Custom"
        else:
             types_part = f"Types_{types_str}"

    # Inversions part
    # Note: actual inversions depend on the chord type, this describes the requested range
    requested_invs_str = "-".join(map(str, sorted(list(set(args.inversions)))))
    inversions_part = f"Invs_{requested_invs_str}"
    if args.skip_root:
        inversions_part += "_NoRootPos"

    # Combine parts
    base_filename = f"{roots_part}_{types_part}_{inversions_part}"

    # Sanitize filename: replace '#' with 's', remove other invalid chars
    sanitized_filename = base_filename.replace("#", "s")
    sanitized_filename = re.sub(r'[\\/*?:"<>|]', "", sanitized_filename)

    return f"{sanitized_filename}.pdf"

# --- Main Execution ---
def main():
    """
    Main function to parse arguments and generate chord diagrams.
    """
    parser = argparse.ArgumentParser(description="Generate musical chord diagrams and save them to PDF.")
    parser.add_argument("-r", "--roots", nargs='+', default=["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"],
                        help="List of root notes (e.g., C G# F). Defaults to all 12 chromatic notes.")
    parser.add_argument("-t", "--types", nargs='+', default=["major", "minor", "7", "minor7", "maj7"],
                        help="List of chord types (e.g., major 7 maj7). Defaults to major, minor, 7, minor7, maj7.")
    parser.add_argument("-i", "--inversions", type=int, nargs='+', default=[0, 1, 2, 3],
                        help="List of inversion numbers (e.g., 0 1 2). Max valid inversion depends on chord type. Defaults to 0, 1, 2, 3.")
    parser.add_argument("-o", "--output", default=None, # Default to None, indicating auto-generate
                        help="Output PDF filename. If omitted, a descriptive name is generated automatically.")
    parser.add_argument("--skip-root", action='store_true',
                        help="Skip generating root position chords (only generate inversions).")


    args = parser.parse_args()

    # --- Filename Generation ---
    if args.output is None:
        output_filename = generate_filename(args)
    else:
        # Use user-provided name, ensure it ends with .pdf
        output_filename = args.output
        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"
    # -------------------------

    # Validate chord types and roots from arguments
    valid_types = {"major", "minor", "7", "minor7", "maj7"}
    valid_roots = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"}

    # Filter invalid types/roots specified by user
    requested_roots = [r for r in args.roots if r in valid_roots]
    invalid_roots = [r for r in args.roots if r not in valid_roots]
    if invalid_roots:
        logging.warning(f"Ignoring invalid root notes specified: {', '.join(invalid_roots)}")

    requested_types = [t for t in args.types if t in valid_types]
    invalid_types = [t for t in args.types if t not in valid_types]
    if invalid_types:
         logging.warning(f"Ignoring invalid chord types specified: {', '.join(invalid_types)}")

    if not requested_roots or not requested_types:
        logging.error("No valid roots or types specified. Exiting.")
        return


    logging.info(f"Generating diagrams for roots: {', '.join(requested_roots)}")
    logging.info(f"Chord types: {', '.join(requested_types)}")
    logging.info(f"Requested inversions: {', '.join(map(str, sorted(list(set(args.inversions)))))}")
    logging.info(f"Output file: {output_filename}") # Log the final filename

    count = 0
    # Use the generated or specified filename
    with PdfPages(output_filename) as pdf:
        for root in requested_roots:
            for chord_type in requested_types:
                # Determine number of notes for inversion validation
                num_notes = len({
                    "major": [0, 4, 7], "minor": [0, 3, 7], "7": [0, 4, 7, 10],
                    "minor7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11]
                }[chord_type])

                # Filter requested inversions to only valid ones for this chord type
                valid_requested_inversions = [inv for inv in args.inversions if 0 <= inv < num_notes]

                if args.skip_root and 0 in valid_requested_inversions:
                     valid_requested_inversions.remove(0)

                active_inversions = sorted(list(set(valid_requested_inversions))) # Unique & sorted


                for inversion in active_inversions:
                    try:
                        notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                        # Plotting happens INSIDE plot_chord_diagram now
                        plot_chord_diagram(notes, keys, title)
                        pdf.savefig(bbox_inches="tight") # Save the current figure to the PDF
                        plt.close() # Close the figure to free memory
                        count += 1
                        logging.info(f"Generated: {title}")
                    except ValueError as e:
                        # Log value errors (like invalid inversion for chord type) which might occur here
                        logging.error(f"Could not generate '{root} {chord_type}' (Inversion {inversion}): {e}")
                    except Exception as e:
                        logging.error(f"An unexpected error occurred generating '{root} {chord_type}' (Inversion {inversion}): {e}", exc_info=True) # Log full traceback for unexpected errors


    logging.info(f"Finished! Created {output_filename} containing {count} chord diagrams.")


if __name__ == "__main__":
    main()