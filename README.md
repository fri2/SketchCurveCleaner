# Sketch Curve Cleaner for Autodesk Fusion 360

## Version

Current version: **16.0.0**

**Sketch Curve Cleaner** is an Autodesk Fusion 360 add-in that helps preview and clean duplicated or overlapping sketch curves.

The source code, comments, installation documentation, and repository documentation are written in English.  
The Fusion 360 command UI is localized at runtime according to the language selected by the user in Fusion 360, when that language can be detected.

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
4. drawing replacement curves as temporary construction geometry directly in the target sketch.

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
- replacement curves are created as temporary construction geometry directly in
  the target sketch;
- these temporary curves are marked with an internal Fusion attribute;
- they are automatically removed before a new **Test**, before **Apply**, on
  **Cancel**, and when the command closes.

This preview does not provide red/green coloring, but it is designed to be
visible and geometrically aligned with the actual sketch.


## Versioning

The add-in version is defined in the Python source:

```python
ADDIN_VERSION = "16.0.0"
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
```

The final Fusion 360 installation path is:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn
```
