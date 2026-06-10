# SVG pre-cleaner

`clean_svg.py` is an external helper script stored in the same source directory
as the Fusion 360 add-in:

```text
SketchCurveCleanerLocalizedAddIn/
├── SketchCurveCleanerLocalizedAddIn.py
├── clean_svg.py
└── README.md
```

It is **not** copied into Fusion 360 by `install_to_fusion360.bat`.

## Why this script exists

Imported SVG files can become very slow inside Fusion 360 because the Fusion API
has to expose every sketch curve one by one. Cleaning the SVG before import is
usually much faster.

## Usage

From a terminal opened in this folder:

```bash
python clean_svg.py input.svg
```

This creates:

```text
input_cleaned.svg
```

With an explicit output file:

```bash
python clean_svg.py input.svg -o output_cleaned.svg
```

With a custom tolerance in SVG user units:

```bash
python clean_svg.py input.svg -t 0.01
```

## Supported SVG geometry

The script cleans simple straight-line geometry:

```text
<line>
<polyline>
<polygon>
<path> with only M, L, H, V and Z commands
```

It removes duplicate/overlapping collinear line segments and writes one cleaned
group named:

```text
cleaned_line_segments
```

## Important limitations

The script deliberately preserves unsupported or risky SVG content unchanged:

```text
- Bézier curves
- arcs
- paths with C/S/Q/T/A commands
- elements with transform attributes
- complex styling logic
```

This is intentional. The script is a conservative pre-cleaner for straight-line
SVG content before Fusion import, not a full SVG optimizer.

Always keep the original SVG.
