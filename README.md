# Sketch Curve Cleaner for Autodesk Fusion 360

## Version

Current version: **23.0.0**

**Sketch Curve Cleaner** is an Autodesk Fusion 360 add-in that helps preview and clean duplicated or overlapping sketch curves.

The source code, comments, installation documentation, and repository documentation are written in English.  
The Fusion 360 command UI is localized at runtime according to the language selected by the user in Fusion 360, when that language can be detected.


## Important warning for imported SVG sketches

Imported SVG files can produce very dense Fusion 360 sketches.

A visually simple SVG can become:

```text
- thousands of tiny line segments;
- many fitted splines;
- many control-point splines;
- duplicated curves created by import/export round trips;
- fragmented contours that are expensive to inspect through the Fusion API.
```

Because of this, clicking **Test** on a large imported SVG can be slow and may
make Fusion look as if it is looping or frozen.

Recommended precautions:

```text
1. Save the Fusion design before running the add-in.
2. Work on a copy of the sketch when possible.
3. Keep "Treat near-straight SVG/imported splines as lines" disabled by default.
4. Keep "Allow large sketch analysis" disabled by default.
5. Run Test first on a small extract of the SVG.
6. Split or simplify the SVG before importing when the sketch is very dense.
7. Clean the SVG in Inkscape or another vector editor before import.
```

Do not enable:

```text
Treat near-straight SVG/imported splines as lines
Allow large sketch analysis
```

on a large imported SVG unless you knowingly accept that Fusion may become slow.

Version 20 displays this warning directly in the Fusion 360 command dialog.


## Author

**RICHARD Francois**

## License

This project is licensed under **GPL-3.0-only**.

SPDX identifier:

```text
GPL-3.0-only
```

See the [`LICENSE`](LICENSE) file for the full license text.

## Features

The add-in provides a Fusion 360 command named:

```text
Clean Sketch Overlaps
```

The command includes:

- **Test**: preview the cleanup without applying permanent changes.
- **Apply**: apply the cleanup to the active or selected sketch.
- **Cancel**: close the command and remove the temporary preview.

The preview works by:

1. deleting any previous temporary preview curves;
2. analyzing the target sketch;
3. selecting the source curves that would be deleted or replaced;
4. updating the command summary without drawing temporary preview geometry.

## Cleanup options

The command dialog is intentionally conservative by default. The safest workflow
is to keep the default options, click **Test**, review the selected source curves
and the temporary construction preview, then click **Apply** only when the result
looks correct.

### Delete exact duplicate curves

Default: **enabled**

This option removes curves that represent the same geometry within the selected
tolerance.

Typical examples:

- two identical lines on top of each other;
- two identical arcs with the same center, radius and angle range;
- two identical circles with the same center and radius;
- duplicate curves created by DXF import, copy/paste, projection, or export/import
  round trips.

The add-in keeps one representative curve and deletes the duplicates. When
possible, it prefers to keep the curve that appears more important for design
intent, for example one with constraints, dimensions, or fixed state.

Recommended use:

- keep this option enabled in most cases;
- use **Test** first when the sketch contains dimensions or constraints;
- be careful if the duplicates intentionally represent different manufacturing
  operations on the same contour.

### Split/merge partially overlapping straight lines

Default: **enabled**

This option detects straight line segments that are collinear and overlap
partially. Instead of simply deleting one line, the add-in computes the useful
covered span and creates replacement line segments.

Typical examples:

```text
Original:
A────────────D
    B────────────E

Result:
A────────────────E
```

or, depending on how the overlaps are arranged, several non-overlapping output
segments may be created.

This is useful after:

- importing DXF files from CAD/CAM tools;
- exploding geometry;
- copying sketches;
- receiving files with repeated or fragmented contours.

Recommended use:

- keep enabled for laser cutting / DXF cleanup workflows;
- click **Test** and check that the temporary construction preview follows the
  expected contour;
- avoid applying blindly on sketches with heavy parametric constraints unless
  **Merge/delete constrained or dimensioned geometry** is intentionally enabled.



### Treat near-straight SVG/imported splines as lines

Default: **disabled**

This option is designed for sketches created from imported SVG files, but it can be slow on very dense imports. Enable it only when regular line cleanup misses visually straight SVG lines.

A visually straight SVG segment is not always imported into Fusion 360 as a true
`SketchLine`. Depending on the SVG content and the importer, it may become a
very short fitted spline, a control-point spline, or a fragmented set of
segments. If the cleaner only looks at `SketchLine` objects, some superposed
"lines" from SVG imports can be missed.

When this option is enabled, the add-in inspects fitted and control-point splines
and treats them as line candidates only when they are geometrically almost
straight:

```text
- the spline has a usable start point and end point;
- its definition points stay close to the chord from start to end;
- its curve length is close to the chord length;
- the deviation is within the active tolerance plus a small relative allowance.
```

Accepted near-straight splines participate in:

```text
- exact duplicate detection;
- partial overlap detection;
- split/merge of collinear segments.
```

When **Apply** is used, accepted spline-like line segments may be replaced by real
Fusion sketch lines. This is usually desirable for SVG cleanup and laser/DXF
workflows because it simplifies the sketch.

Recommended use:

- keep enabled for SVG imports;
- click **Test** first and inspect the selected curves;
- disable it if you intentionally need to preserve spline objects exactly as
  splines;
- use a conservative tolerance first, for example `0.001 cm`.

Risk:

```text
A very shallow curved spline could be treated as a straight line if the tolerance
is too large.
```

### Split/merge partially overlapping circular curves

Default: **disabled**

This option handles circular overlaps: arcs and circles that share the same or
near-same center and radius.

It can detect cases such as:

- two arcs on the same circle partially covering the same angular range;
- an arc duplicated on top of another arc;
- a full circle overlapping with arcs on the same radius.

This option is disabled by default because circular geometry is more sensitive
than straight lines. Small differences in center, radius, start angle or end
angle can change whether two arcs should really be considered part of the same
curve.

Recommended use:

- enable it only when you know the sketch contains duplicated arcs or circles;
- increase tolerance cautiously if imported arcs are slightly misaligned;
- always use **Test** before **Apply**;
- check the preview carefully around arc endpoints and tangent transitions.

### Also delete projected/reference geometry

Default: **disabled**

Projected/reference geometry is usually linked to other geometry in the design.
Deleting or replacing it can break associativity or remove useful construction
references.

When this option is disabled, the add-in skips protected projected/reference
curves.

Enable this option only if:

- the projected/reference curves are unwanted duplicates;
- you no longer need the projection link;
- the sketch comes from an imported DXF and the reference state is not meaningful;
- you are working on a copy of the design.

Risk:

```text
Projected/reference geometry may be important for downstream sketches,
constraints, dimensions, profiles, or design associativity.
```

### Merge/delete constrained or dimensioned geometry

Default: **disabled**

Constrained or dimensioned curves often carry design intent. Replacing them may
remove constraints or dimensions attached to the original curves.

When this option is disabled, the add-in skips groups that contain constrained,
dimensioned, or fixed geometry where deletion/replacement would be risky.

Enable this option only if:

- you want a geometric cleanup even if constraints/dimensions are lost;
- the sketch is imported and constraints are not useful;
- you already saved a backup or are working on a copy.

Risk:

```text
Dimensions, geometric constraints, fixed states, or parametric intent may be lost.
```

Recommended use:

- leave disabled for parametric design sketches;
- enable only for cleanup/import sketches where geometry quality matters more
  than constraints.

### Merge construction and normal geometry together

Default: **disabled**

Fusion distinguishes normal sketch geometry from construction geometry.

When this option is disabled, the add-in keeps these two categories separate:

```text
normal geometry       → merged only with normal geometry
construction geometry → merged only with construction geometry
```

When enabled, normal and construction geometry may be analyzed together.

The replacement curve follows this rule:

- if any source curve is normal geometry, the replacement is normal geometry;
- if all source curves are construction geometry, the replacement is construction
  geometry.

Enable this option only if construction/normal status is not important for your
workflow.

Risk:

```text
A construction-only helper contour may become normal geometry if it is merged
with normal geometry.
```

Recommended use:

- leave disabled for design sketches;
- enable for dirty DXF cleanup when construction status is accidental or irrelevant.

### Tolerance (cm)

Default: **0.001 cm**, which equals **0.01 mm**.

Fusion 360 stores sketch geometry internally in centimeters, so the command uses
centimeters for the tolerance value.

Useful conversions:

```text
0.0001 cm = 0.001 mm
0.0010 cm = 0.010 mm
0.0100 cm = 0.100 mm
0.1000 cm = 1.000 mm
```

The tolerance controls how close two points, centers, radii, or directions must
be before the add-in considers them equal or compatible.

Recommended values:

| Situation | Suggested tolerance |
|---|---:|
| Clean CAD geometry | 0.0001 cm to 0.001 cm |
| Typical DXF import cleanup | 0.001 cm |
| Slightly noisy imported geometry | 0.002 cm to 0.01 cm |
| Very rough geometry | use with caution |

A larger tolerance can clean more aggressively, but it can also merge geometry
that should remain separate.

Risk:

```text
Too small  → duplicates may not be detected.
Too large  → distinct curves may be merged incorrectly.
```

### Test button

**Test** performs a dry run.

It does not permanently modify the sketch. It:

1. removes any previous temporary preview;
2. analyzes the active or selected sketch;
3. selects the source curves that would be deleted or replaced;
4. creates temporary construction preview curves showing the replacement result;
5. updates the summary in the command dialog.

Use **Test** whenever you change options or tolerance.

### Apply button

**Apply** performs the actual cleanup.

Before applying the plan, the add-in removes temporary preview curves so they are
not accidentally included in the cleanup analysis.

Then it deletes/replaces the curves according to the current options.

Recommended workflow:

```text
1. Open or select the sketch.
2. Start Clean Sketch Overlaps.
3. Keep safe defaults first.
4. Click Test.
5. Inspect the selected curves and temporary construction preview.
6. Adjust options/tolerance if needed.
7. Click Test again.
8. Click Apply only when the preview is correct.
```

### Cancel button

**Cancel** closes the command and removes temporary preview geometry.

No cleanup is applied.



## Geometry support

### Exact duplicate detection

The add-in can detect exact or near-exact duplicates for:

- Lines
- Circles
- Arcs
- Ellipses
- Elliptical arcs
- Fitted splines

### Partial split/merge

The add-in can split/merge partially overlapping geometry for:

- Straight lines
- Circular arcs
- Circles

### Current limitations

Partial split/merge is not currently implemented for:

- Ellipses
- Elliptical arcs
- Splines

These entities are handled only as exact or near-exact duplicates.

## Safety defaults

By default, the add-in is conservative:

- projected/reference geometry is protected;
- constrained or dimensioned geometry is protected from merge/delete operations;
- construction geometry is kept separate from normal geometry.

You can override these behaviors in the command dialog.

Be careful when enabling the following options:

- **Also delete projected/reference geometry**
- **Merge/delete constrained or dimensioned geometry**
- **Merge construction and normal geometry together**

These options can affect design intent, projected associativity, constraints, or dimensions. Test on a copy of the design first.


## Correct Fusion 360 installation path on Windows

The correct Windows installation path for this add-in is:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn
```

In other words, the complete add-in folder must be named:

```text
SketchCurveCleanerLocalizedAddIn
```

and placed inside:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns
```

Do not use the older/wrong path:

```text
%APPDATA%\Autodesk\Autodesk Fusion\API\AddIns
```

## Installation on Windows

1. Close Fusion 360.
2. Copy the full folder `SketchCurveCleanerLocalizedAddIn` to:

   ```text
   %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns
   ```

3. Start Fusion 360.
4. Open:

   ```text
   Utilities > Scripts and Add-Ins > Add-Ins
   ```

5. Select `SketchCurveCleanerLocalizedAddIn`.
6. Click **Run**.
7. Enable **Run on Startup** if you want the command to be loaded automatically.

## Installation on macOS

1. Close Fusion 360.
2. Copy the full folder `SketchCurveCleanerLocalizedAddIn` to the Fusion 360 AddIns folder.

Typical location:

```text
~/Library/Application Support/Autodesk/Autodesk Fusion/API/AddIns
```

3. Start Fusion 360.
4. Open:

```text
Utilities > Scripts and Add-Ins > Add-Ins
```

5. Select `SketchCurveCleanerLocalizedAddIn`.
6. Click **Run**.
7. Enable **Run on Startup** if desired.

## Usage

1. Open a Fusion 360 design.
2. Edit the sketch you want to clean, or select a sketch in the browser.
3. Run **Clean Sketch Overlaps** from the toolbar.
4. Choose the cleanup options.
5. Click **Test** to preview the changes.
6. Review the selected curves and the temporary preview sketch.
7. Click **Apply** to modify the sketch, or **Cancel** to leave it unchanged.

## Localization

The code uses a small internal localization table.

Currently included UI languages:

- English
- French

English is used as fallback if Fusion 360's language cannot be detected.

The implementation attempts to read Fusion 360's user language through the application preferences. The command labels, option labels, result summaries, warnings, and messages are then selected from the localization dictionary.

## Repository structure

```text
SketchCurveCleanerLocalizedAddIn/
├── SketchCurveCleanerLocalizedAddIn.py
├── SketchCurveCleanerLocalizedAddIn.manifest
├── README.md
└── LICENSE
```

## Development notes

The Python source file is intentionally documented with detailed docstrings.

The comments and docstrings describe:

- the role of each major class;
- the role of each function;
- the parameters passed to functions;
- return values when applicable;
- the geometry planning flow;
- the preview flow;
- the Fusion 360 command registration flow.

The add-in is structured around a non-destructive planning step:

```text
Read command options
↓
Analyze the target sketch
↓
Build a CleanupPlan
↓
Preview the CleanupPlan
↓
Apply the CleanupPlan only if the user confirms
```

## Important technical notes

Fusion 360's API uses centimeters internally.

Default tolerance:

```python
DEFAULT_TOLERANCE_CM = 0.001
```

This corresponds to:

```text
0.001 cm = 0.01 mm
```

For low-precision imported DXF sketches, a larger tolerance may be useful, for example:

```text
0.01 cm = 0.1 mm
```

## Disclaimer

This add-in modifies sketch geometry. Always test on a copy of the design before using it on production work.

Projected geometry, constrained geometry, dimensions, and construction geometry may carry design intent. Enabling aggressive cleanup options can break that intent.


## Reliable construction-geometry preview

Version 11 deliberately avoids Custom Graphics and dialog SVG previews.

In practice, those preview methods can be invisible or misleading depending on
the Fusion 360 sketch editing context. Version 11 uses a more robust approach:

- curves that would be deleted or replaced are selected in the active sketch;
- replacement curves are not drawn during Test in version 22;
- these temporary curves are marked with an internal Fusion attribute;
- they are automatically removed before a new **Test**, before **Apply**, on
  **Cancel**, and when the command closes.

Version 22 disables this preview mode to improve performance on dense SVG imports.


## Versioning

The add-in version is defined in the Python source:

```python
ADDIN_VERSION = "23.0.0"
```

The same version is also stored in the Fusion manifest file and displayed in the
Fusion 360 command dialog. This makes it easier to check which installed version
is currently running.




## Installation helper files

This repository/package keeps the installation helper files directly inside the
`SketchCurveCleanerLocalizedAddIn` folder:

```text
SketchCurveCleanerLocalizedAddIn/
├── SketchCurveCleanerLocalizedAddIn.py
├── SketchCurveCleanerLocalizedAddIn.manifest
├── README.md
├── LICENSE
├── .gitignore
├── install_to_fusion360.bat
├── uninstall_from_fusion360.bat
└── INSTALL.md
```

The installer copies only the real Fusion 360 add-in files.

The following helper files are **excluded** during installation and are not copied
to Fusion 360:

```text
install_to_fusion360.bat
uninstall_from_fusion360.bat
INSTALL.md
clean_svg.py
SVG_PRE_CLEANER.md
```

The final Fusion 360 installation path is:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn
```


## Performance notes for SVG imports

SVG imports can create very large sketches. A drawing that visually looks simple
may become hundreds or thousands of small splines or micro-segments inside
Fusion 360.

For this reason, version 18 is intentionally more conservative:

```text
- SVG spline analysis is disabled by default.
- At most 300 imported splines are analyzed when SVG spline mode is enabled.
- At most 24 definition points per spline are inspected.
- The add-in no longer calls spline.length during near-straight detection.
- Preview geometry is skipped when more than 300 replacement curves would be drawn.
- Selection is limited to 300 curves to keep Fusion responsive.
```

If Fusion feels like it is looping:

```text
1. Leave "Treat near-straight SVG/imported splines as lines" disabled.
2. Run Test with only exact duplicates and straight-line merge enabled.
3. If missing overlaps remain, enable SVG spline mode and try again.
4. Use a small tolerance first, for example 0.001 cm.
5. If the sketch is huge, split the SVG before importing or clean it in Inkscape first.
```

When the performance limits are reached, the Test summary reports skipped splines,
limited selection, or skipped preview geometry.


## Version 19: no-loop guard for dense SVG sketches

Version 19 adds a hard safe-mode guard before the add-in starts expensive sketch
analysis.

Before **Test** or **Apply**, the add-in now counts sketch curve collections
without materializing every curve object. If the sketch is too dense, the command
stops immediately and displays a diagnostic summary instead of continuing.

Default safe limits:

```text
MAX_SAFE_TOTAL_CURVES = 1200
MAX_SAFE_LINES        = 1000
MAX_SAFE_SPLINES      = 150
```

A new option is available in the dialog:

```text
Allow large sketch analysis (can be slow)
```

Leave it disabled by default. Enable it only when you knowingly want to run the
analysis on a large sketch and you accept that Fusion may become slow.

This guard is especially important for imported SVG files, because a visually
simple SVG may become thousands of sketch splines or micro-segments inside Fusion.

If the guard blocks the test, recommended actions are:

```text
1. Split the SVG into smaller parts before importing.
2. Clean duplicates in Inkscape before import.
3. Convert straight SVG segments to simple paths/lines before import.
4. Run the add-in on smaller sketches instead of one massive sketch.
5. Only then consider enabling "Allow large sketch analysis".
```

Also, when SVG spline mode is disabled, exact duplicate scanning no longer
materializes all spline entities. This prevents a common slow path on dense SVG
imports.


## Version 21: faster SVG workflow

Version 21 adds two complementary performance improvements.

### 1. Fusion add-in fast modes

The Fusion command now includes:

```text
Selected geometry only
Line-only fast mode for SVG imports
```

Use **Selected geometry only** when the imported SVG sketch is too dense. Select a
small group of curves in the sketch, then run **Test**. The add-in will analyze
only the selected curves instead of scanning the whole sketch.

Use **Line-only fast mode for SVG imports** when you mainly want to clean
straight SVG/DXF linework. In this mode, the add-in focuses on line-like geometry
and skips slower circular/spline-wide analysis.

Recommended SVG workflow inside Fusion:

```text
1. Select a small zone of the imported SVG sketch.
2. Enable "Selected geometry only".
3. Enable "Line-only fast mode for SVG imports".
4. Keep "Treat near-straight SVG/imported splines as lines" disabled at first.
5. Click Test.
6. Enable SVG spline mode only on a small selected area if needed.
```

### 2. External SVG pre-cleaner in the same directory

The package now includes an external Python helper in the same directory as the
add-in:

```text
SketchCurveCleanerLocalizedAddIn/clean_svg.py
```

It is documented in:

```text
SketchCurveCleanerLocalizedAddIn/SVG_PRE_CLEANER.md
```

Basic usage:

```bash
python clean_svg.py input.svg
```

This creates:

```text
input_cleaned.svg
```

The pre-cleaner works before Fusion import. This is usually much faster than
cleaning thousands of SVG-generated sketch curves through the Fusion API.

The installer excludes this helper from the Fusion 360 AddIns folder. It remains
a source/repository tool, not a Fusion runtime file.


## Version 22: preview geometry disabled

Version 22 removes temporary preview geometry from the **Test** workflow.

Earlier versions created construction curves in the active sketch to show the
replacement result. On dense imported SVG sketches, this could be very expensive
because Fusion had to create many temporary sketch curves, recompute the sketch,
refresh the display, and later delete those curves.

In version 22, **Test** does only this:

```text
1. removes old temporary preview artifacts from previous versions;
2. analyzes the sketch or selected geometry;
3. selects a limited sample of affected source curves;
4. updates the command summary.
```

It does **not** create replacement preview curves anymore.

This should improve responsiveness, especially for imported SVG sketches.

Recommended workflow for dense SVG imports:

```text
1. Use clean_svg.py before importing when possible.
2. In Fusion, enable "Selected geometry only".
3. Enable "Line-only fast mode for SVG imports".
4. Keep SVG spline analysis disabled at first.
5. Click Test.
6. Read the summary.
7. Apply only on small, controlled selections.
```

Trade-off:

```text
The Test command is faster and safer, but it no longer draws the replacement
geometry before Apply.
```


## Version 23: mixed SVG + normal sketch cleanup

Version 23 fixes an important mixed-sketch case.

Problem in earlier versions:

```text
If a normal Fusion sketch contained duplicated sketch entities and also many
SVG-imported splines in the same sketch, the SVG density guard could block the
whole Test. As a result, ordinary duplicated sketch lines/arcs/circles were not
removed.
```

New behavior:

```text
- When SVG spline analysis is disabled, dense SVG/spline entities are ignored by
  the safe-mode guard.
- Standard sketch geometry is still analyzed:
  - SketchLine
  - SketchArc
  - SketchCircle
  - SketchEllipse
  - SketchEllipticalArc
- Normal duplicated sketch elements can therefore be cleaned even when a dense
  imported SVG exists in the same sketch.
```

The Test summary now reports:

```text
Curves considered by safe-mode guard
Splines/SVG ignored because SVG analysis is disabled
```

Recommended mixed-sketch workflow:

```text
1. Leave "Treat near-straight SVG/imported splines as lines" disabled.
2. Leave "Allow large sketch analysis" disabled.
3. Run Test.
4. Apply only if the summary shows the expected standard sketch duplicates.
5. Treat SVG geometry separately with clean_svg.py or Selected geometry only.
```
