# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-only
#
# Sketch Curve Cleaner for Autodesk Fusion 360
# Copyright (C) 2026 RICHARD Francois
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only,
# as published by the Free Software Foundation.
#
"""
Fusion 360 Add-In - Sketch Curve Cleaner with localized UI and preview.

Source code, comments and installation documentation are written in English.
The user-facing Fusion 360 command UI is localized according to the Fusion 360
user language when it can be detected. English is used as fallback.

Main features:
- Preview before applying changes.
- Exact duplicate removal for common sketch curves.
- Partial merge/split of overlapping straight lines.
- Partial merge/split of overlapping circular curves: arcs and circles.
- Optional processing of projected/reference geometry.
- Optional processing of constrained/dimensioned geometry.
- Optional merge of construction geometry with normal geometry.

Important limitation:
Partial curve merge supports straight lines, near-straight SVG-imported
splines, and circular curves (arcs/circles). Ellipses and non-straight
splines are handled only as exact duplicates.
"""

import math
import traceback

import adsk.core
import adsk.fusion


# -----------------------------------------------------------------------------
# Developer documentation note
# -----------------------------------------------------------------------------
#
# This file intentionally contains detailed docstrings for most functions and
# classes. They describe the purpose of each unit, the parameters expected by
# Fusion 360 or by the cleaner itself, and the returned values when applicable.
# The comments are written in English so that the add-in can be maintained and
# shared more easily, while the command UI remains localized at runtime.
#

# -----------------------------------------------------------------------------
# Add-in identity
# -----------------------------------------------------------------------------

ADDIN_NAME = "Sketch Curve Cleaner"
ADDIN_VERSION = "23.0.0"
ADDIN_AUTHOR = "RICHARD Francois"
ADDIN_LICENSE = "GPL-3.0-only"
ADDIN_COPYRIGHT = "Copyright (C) 2026 RICHARD Francois"
CMD_ID = "FRI2_SketchCurveCleaner_LocalizedPreview_v2"
CMD_NAME_KEY = "cmd_name"
CMD_DESCRIPTION_KEY = "cmd_description"
PREVIEW_SKETCH_NAME = "__PREVIEW_Clean_Sketch_Overlaps__"

# Fusion API uses centimeters internally.
# 0.001 cm = 0.01 mm.
DEFAULT_TOLERANCE_CM = 0.001
# Performance guardrails for very dense imported SVG sketches.
MAX_SVG_SPLINES_TO_ANALYZE = 300
MAX_SPLINE_DEFINITION_POINTS = 24
MAX_PREVIEW_REPLACEMENT_CURVES = 300
MAX_PREVIEW_SELECTIONS = 300
# Version 22: Test no longer creates temporary preview geometry.
PREVIEW_GEOMETRY_ENABLED = False
# Hard fail-fast limits used before any expensive Fusion API iteration.
MAX_SAFE_TOTAL_CURVES = 1200
MAX_SAFE_LINES = 1000
MAX_SAFE_SPLINES = 150

# Try these panel IDs first. Fusion internal IDs can vary, so the add-in also
# falls back to known Scripts/Add-Ins panels when needed.
PANEL_CANDIDATES = [
    "SketchModifyPanel",
    "SolidModifyPanel",
    "SurfaceModifyPanel",
    "FormModifyPanel",
]

FALLBACK_PANEL_CANDIDATES = [
    "SolidScriptsAddinsPanel",
    "ToolsAddinsPanel",
]

WORKSPACE_CANDIDATES = [
    "FusionSolidEnvironment",
    "FusionSketchEnvironment",
    "FusionSurfaceEnvironment",
    "FusionFormEnvironment",
]

_handlers = []
_added_controls = []
_added_command_definition = None


# -----------------------------------------------------------------------------
# Localization
# -----------------------------------------------------------------------------

_STRINGS = {
    "en": {
        "cmd_name": "Clean Sketch Overlaps",
        "cmd_description": "Preview and clean duplicate or overlapping sketch curves.",
        "version_label": "Version",
        "no_sketch": (
            "No active or selected sketch was found.\n\n"
            "Edit a sketch, or select a sketch in the Fusion browser, then run the command again."
        ),
        "intro": (
            "Use Test to preview the cleanup. Apply modifies the sketch. "
            "Temporary preview geometry is created for merged replacement curves."
        ),
        "settings_group": "Cleanup options",
        "selected_only": "Selected geometry only",
        "line_only_fast": "Line-only fast mode for SVG imports",
        "selected_none": "Selected geometry only is enabled, but no supported sketch curves are selected. Select a few curves in the target sketch, then click Test again.",
        "delete_exact": "Delete exact duplicate curves",
        "merge_lines": "Split/merge partially overlapping straight lines",
        "svg_splines": "Treat near-straight SVG/imported splines as lines (slower)",
        "allow_large": "Allow large sketch analysis (can be slow)",
        "large_blocked_title": "Large sketch analysis blocked by safe mode.",
        "large_blocked_hint": "The sketch is too dense for a safe Test. Split/clean the SVG first, disable costly options, or enable large sketch analysis knowingly.",
        "mixed_svg_note": "Dense SVG/spline geometry is ignored when SVG spline analysis is disabled. Standard sketch geometry can still be cleaned.",
        "svg_warning": "Warning: imported SVG sketches can contain thousands of micro-segments or splines. Test can become very slow. Keep SVG spline analysis and large sketch analysis disabled unless you are working on a small sketch or a copy.",
        "merge_circular": "Split/merge partially overlapping circular curves (arcs/circles)",
        "allow_reference": "Also delete projected/reference geometry",
        "allow_constrained": "Merge/delete constrained or dimensioned geometry",
        "merge_construction": "Merge construction and normal geometry together",
        "tolerance": "Tolerance (cm)",
        "test": "Test",
        "apply": "Apply",
        "cancel": "Cancel",
        "summary": "Preview / result summary",
        "preview_created": "Preview created.",
        "preview_failed": "Preview could not be fully created.",
        "cleanup_completed": "Cleanup completed.",
        "nothing_to_preview": "Nothing to preview.",
        "test_hint": "Click Test to analyze the active or selected sketch.",
        "result_sketch": "Sketch",
        "result_tolerance": "Tolerance",
        "result_exact": "Exact duplicates to delete",
        "result_line_groups": "Overlapping line groups",
        "result_line_delete": "Lines to replace",
        "result_line_create": "Merged lines to create",
        "result_svg_splines": "Near-straight imported splines treated as lines",
        "result_svg_skipped": "Imported splines skipped by performance limit",
        "result_ignored_splines": "Splines/SVG ignored because SVG analysis is disabled",
        "result_active_count": "Curves considered by safe-mode guard",
        "result_preview_limited": "Preview geometry skipped by performance limit",
        "result_selection_limited": "Selection limited for performance",
        "result_selected_only": "Selected geometry only",
        "result_selected_count": "Selected curves used for analysis",
        "result_line_only_fast": "Line-only fast mode",
        "result_circular_groups": "Overlapping circular curve groups",
        "result_circular_delete": "Circular curves to replace",
        "result_circular_create": "Merged circular curves to create",
        "result_protected": "Protected/reference curves skipped",
        "result_constrained": "Constrained/dimensioned groups skipped",
        "result_total_delete": "Total curves to delete/replace",
        "preview_note": (
            "Curves that would be deleted/replaced are selected. "
            "Merged replacement curves are shown in a temporary preview sketch."
        ),
        "warning_reference": (
            "Warning: projected/reference geometry can be important for design associativity."
        ),
        "warning_constrained": (
            "Warning: constrained or dimensioned geometry may lose dimensions/constraints."
        ),
        "warning_construction": (
            "Warning: merging construction and normal geometry can change sketch intent."
        ),
        "partial_limit": (
            "Note: partial split/merge supports straight lines, near-straight SVG/imported splines, "
            "and circular arcs/circles. Ellipses and non-straight splines are processed only as exact duplicates."
        ),
        "addin_loaded_no_panel": (
            "The add-in was loaded, but no suitable toolbar panel was found. "
            "The command definition was created, but Fusion did not expose the expected panels."
        ),
    },
    "fr": {
        "cmd_name": "Nettoyer les superpositions d’esquisse",
        "cmd_description": "Prévisualiser et nettoyer les courbes d’esquisse dupliquées ou superposées.",
        "version_label": "Version",
        "no_sketch": (
            "Aucune esquisse active ou sélectionnée n’a été trouvée.\n\n"
            "Édite une esquisse, ou sélectionne une esquisse dans le navigateur Fusion, puis relance la commande."
        ),
        "intro": (
            "Utilise Test pour prévisualiser le nettoyage. Appliquer modifie l’esquisse. "
            "Une prévisualisation temporaire est créée pour afficher les courbes fusionnées."
        ),
        "settings_group": "Options de nettoyage",
        "selected_only": "Géométrie sélectionnée uniquement",
        "line_only_fast": "Mode rapide lignes seulement pour imports SVG",
        "selected_none": "L’option géométrie sélectionnée uniquement est activée, mais aucune courbe d’esquisse prise en charge n’est sélectionnée. Sélectionnez quelques courbes dans l’esquisse cible, puis cliquez à nouveau sur Test.",
        "delete_exact": "Supprimer les courbes exactement dupliquées",
        "merge_lines": "Découper/fusionner les lignes droites partiellement superposées",
        "svg_splines": "Traiter les splines SVG/importées quasi droites comme des lignes (plus lent)",
        "allow_large": "Autoriser l’analyse des grandes esquisses (peut être lent)",
        "large_blocked_title": "Analyse de grande esquisse bloquée par le mode sécurisé.",
        "large_blocked_hint": "L’esquisse est trop dense pour un Test sûr. Découpe/nettoie le SVG d’abord, désactive les options coûteuses, ou autorise volontairement l’analyse des grandes esquisses.",
        "mixed_svg_note": "La géométrie SVG/spline dense est ignorée quand l’analyse des splines SVG est désactivée. La géométrie d’esquisse standard peut quand même être nettoyée.",
        "svg_warning": "Attention : les esquisses importées depuis SVG peuvent contenir des milliers de micro-segments ou de splines. Test peut devenir très lent. Gardez l’analyse des splines SVG et l’analyse des grandes esquisses désactivées, sauf sur une petite esquisse ou une copie.",
        "merge_circular": "Découper/fusionner les courbes circulaires partiellement superposées (arcs/cercles)",
        "allow_reference": "Supprimer aussi les géométries projetées/référencées",
        "allow_constrained": "Fusionner/supprimer les géométries contraintes ou cotées",
        "merge_construction": "Fusionner géométrie de construction et géométrie normale",
        "tolerance": "Tolérance (cm)",
        "test": "Test",
        "apply": "Appliquer",
        "cancel": "Annuler",
        "summary": "Résumé de prévisualisation / résultat",
        "preview_created": "Prévisualisation créée.",
        "preview_failed": "La prévisualisation n’a pas pu être entièrement créée.",
        "cleanup_completed": "Nettoyage terminé.",
        "nothing_to_preview": "Rien à prévisualiser.",
        "test_hint": "Clique sur Test pour analyser l’esquisse active ou sélectionnée.",
        "result_sketch": "Esquisse",
        "result_tolerance": "Tolérance",
        "result_exact": "Doublons exacts à supprimer",
        "result_line_groups": "Groupes de lignes superposées",
        "result_line_delete": "Lignes à remplacer",
        "result_line_create": "Lignes fusionnées à créer",
        "result_svg_splines": "Splines importées quasi droites traitées comme lignes",
        "result_svg_skipped": "Splines importées ignorées par limite de performance",
        "result_ignored_splines": "Splines/SVG ignorées car l’analyse SVG est désactivée",
        "result_active_count": "Courbes prises en compte par le garde-fou",
        "result_preview_limited": "Prévisualisation géométrique ignorée par limite de performance",
        "result_selection_limited": "Sélection limitée pour les performances",
        "result_selected_only": "Géométrie sélectionnée uniquement",
        "result_selected_count": "Courbes sélectionnées utilisées pour l’analyse",
        "result_line_only_fast": "Mode rapide lignes seulement",
        "result_circular_groups": "Groupes de courbes circulaires superposées",
        "result_circular_delete": "Courbes circulaires à remplacer",
        "result_circular_create": "Courbes circulaires fusionnées à créer",
        "result_protected": "Courbes projetées/référencées ignorées",
        "result_constrained": "Groupes contraints/cotés ignorés",
        "result_total_delete": "Total de courbes à supprimer/remplacer",
        "preview_note": (
            "Les courbes qui seraient supprimées/remplacées sont sélectionnées. "
            "Les courbes fusionnées sont affichées dans une esquisse temporaire."
        ),
        "warning_reference": (
            "Attention : les géométries projetées/référencées peuvent être importantes pour l’associativité du modèle."
        ),
        "warning_constrained": (
            "Attention : les géométries contraintes ou cotées peuvent perdre leurs contraintes/dimensions."
        ),
        "warning_construction": (
            "Attention : fusionner géométrie de construction et géométrie normale peut modifier l’intention de conception."
        ),
        "partial_limit": (
            "Note : la découpe/fusion partielle prend en charge les lignes droites, les splines SVG/importées quasi droites, "
            "et les arcs/cercles. Les ellipses et splines non droites sont traitées uniquement comme doublons exacts."
        ),
        "addin_loaded_no_panel": (
            "L’add-in est chargé, mais aucun panneau de barre d’outils adapté n’a été trouvé. "
            "La commande a été créée, mais Fusion n’a pas exposé les panneaux attendus."
        ),
    },
}

def detect_language():
    """Return a small language code such as 'en' or 'fr'."""
    try:
        app = adsk.core.Application.get()
        lang = app.preferences.generalPreferences.userLanguage

        # Compare with known enum names when available.
        try:
            if lang == adsk.core.UserLanguages.FrenchLanguage:
                return "fr"
            if lang == adsk.core.UserLanguages.EnglishLanguage:
                return "en"
        except:
            pass

        text = str(lang).lower()
        if "french" in text or "fran" in text or text.startswith("fr"):
            return "fr"
        if "english" in text or text.startswith("en"):
            return "en"

    except:
        pass

    return "en"


def tr(key):
    """
    Return the localized user-interface string for a translation key.
    
        Parameters:
            key (str): Key to look up in the localization dictionary.
    
        Returns:
            str: Localized string matching the current Fusion 360 language.
                 English is used as fallback when the key or language is missing.
    """
    lang = detect_language()
    return _STRINGS.get(lang, _STRINGS["en"]).get(key, _STRINGS["en"].get(key, key))


# -----------------------------------------------------------------------------
# Settings and plan containers
# -----------------------------------------------------------------------------

class CleanupSettings:
    """
    Container for all user-selectable cleanup options.
    
        This class stores the state of the command dialog: tolerance, exact
        duplicate removal, partial merge options, and safety switches for
        reference, constrained and construction geometry.
    
        Attributes:
            tolerance_cm (float): Geometric tolerance in centimeters.
            delete_exact_duplicates (bool): Enables exact duplicate deletion.
            merge_partially_overlapping_lines (bool): Enables partial line merge.
            merge_partially_overlapping_circular_curves (bool): Enables partial
                arc/circle merge.
            treat_near_straight_splines_as_lines (bool): Treats SVG/imported
                fitted/control-point splines that are geometrically straight
                as line candidates.
            allow_reference_geometry (bool): Allows projected/reference geometry
                to be changed.
            allow_constrained_or_dimensioned (bool): Allows constrained or
                dimensioned geometry to be changed.
            merge_construction_and_normal (bool): Allows construction geometry
                and normal geometry to be treated together.
    """
    def __init__(self):
        """
        Initialize cleanup settings with safe default values.
        
            Parameters:
                self (CleanupSettings): Instance being initialized.
        
            Returns:
                None.
        """
        self.tolerance_cm = DEFAULT_TOLERANCE_CM
        self.delete_exact_duplicates = True
        self.merge_partially_overlapping_lines = True
        self.merge_partially_overlapping_circular_curves = False
        self.treat_near_straight_splines_as_lines = False
        self.allow_large_sketch_analysis = False
        self.selected_geometry_only = False
        self.selected_curves = None
        self.line_only_fast_mode = False
        self.allow_reference_geometry = False
        self.allow_constrained_or_dimensioned = False
        self.merge_construction_and_normal = False


class CleanupPlan:
    """
    Represents the full set of changes proposed for one sketch.
    
        The plan is built during Test or Apply. It contains the curves to delete,
        the groups of lines/arcs to replace, skipped objects, and the settings
        used to compute the result.
    
        Attributes:
            sketch (adsk.fusion.Sketch): Target sketch.
            settings (CleanupSettings): Options used for analysis.
            exact_duplicates_to_delete (list): Curves to remove as exact duplicates.
            line_merge_groups (list): Planned straight-line replacements.
            circular_merge_groups (list): Planned arc/circle replacements.
            protected_skipped (int): Count of projected/reference curves skipped.
            constrained_groups_skipped (int): Count of constrained groups skipped.
            unsupported_skipped (int): Count of unsupported objects skipped.
    """
    def __init__(self, sketch, settings):
        """
        Create an empty cleanup plan for a sketch.
        
            Parameters:
                self (CleanupPlan): Instance being initialized.
                sketch (adsk.fusion.Sketch): Sketch to analyze and clean.
                settings (CleanupSettings): User-selected cleanup options.
        
            Returns:
                None.
        """
        self.sketch = sketch
        self.settings = settings
        self.exact_duplicates_to_delete = []
        self.line_merge_groups = []
        self.circular_merge_groups = []
        self.protected_skipped = 0
        self.constrained_groups_skipped = 0
        self.unsupported_skipped = 0
        self.svg_straight_spline_candidates = 0
        self.svg_spline_candidates_skipped = 0
        self.ignored_splines_due_to_svg_disabled = 0
        self.active_guard_curve_count = 0
        self.preview_geometry_limited = False
        self.selection_limited = False

    def all_curves_to_delete_or_replace(self):
        """
        Return every source curve affected by the plan.
        
            This combines exact duplicates and curves that will be replaced by merged
            line or circular geometry. Duplicate references are removed while keeping
            the original order.
        
            Parameters:
                self (CleanupPlan): Current cleanup plan.
        
            Returns:
                list: Unique Fusion sketch curves that would be deleted or replaced.
        """
        curves = []
        curves.extend(self.exact_duplicates_to_delete)

        for group in self.line_merge_groups:
            curves.extend(group["source_curves"])

        for group in self.circular_merge_groups:
            curves.extend(group["source_curves"])

        # Preserve order and remove duplicates by object identity.
        result = []
        seen = set()
        for curve in curves:
            try:
                key = curve.entityToken
            except:
                key = id(curve)

            if key not in seen:
                seen.add(key)
                result.append(curve)

        return result

    def has_changes(self):
        """
        Check whether the plan contains any actual modification.
        
            Parameters:
                self (CleanupPlan): Current cleanup plan.
        
            Returns:
                bool: True when at least one curve would be deleted or replaced.
        """
        return bool(self.all_curves_to_delete_or_replace())


# -----------------------------------------------------------------------------
# Geometry helpers
# -----------------------------------------------------------------------------

def tol(settings):
    """
    Return the active geometric tolerance.
    
        Parameters:
            settings (CleanupSettings): Cleanup options containing the tolerance.
    
        Returns:
            float: Tolerance in centimeters.
    """
    return settings.tolerance_cm


def q(value, settings):
    """
    Quantize a floating-point value using the active tolerance.
    
        Quantization is used to compare geometry robustly despite tiny numerical
        differences from imported DXF or Fusion sketch operations.
    
        Parameters:
            value (float): Value to quantize.
            settings (CleanupSettings): Options containing the tolerance.
    
        Returns:
            int: Rounded integer bucket for the value.
    """
    return int(round(float(value) / tol(settings)))


def qpt(point, settings):
    """
    Quantize a Fusion Point3D into a hashable tuple.
    
        Parameters:
            point (adsk.core.Point3D): Point to convert.
            settings (CleanupSettings): Options containing the tolerance.
    
        Returns:
            tuple[int, int, int]: Quantized x, y and z coordinates.
    """
    return (
        q(point.x, settings),
        q(point.y, settings),
        q(point.z, settings),
    )


def make_point3d(x, y, z=0.0):
    """
    Create a Fusion 360 Point3D object.
    
        Parameters:
            x (float): X coordinate in centimeters.
            y (float): Y coordinate in centimeters.
            z (float): Z coordinate in centimeters. Defaults to 0.0.
    
        Returns:
            adsk.core.Point3D: Newly created Fusion point.
    """
    return adsk.core.Point3D.create(float(x), float(y), float(z))


def dist(a, b):
    """
    Compute the 3D Euclidean distance between two Fusion points.
    
        Parameters:
            a (adsk.core.Point3D): First point.
            b (adsk.core.Point3D): Second point.
    
        Returns:
            float: Distance between the two points in centimeters.
    """
    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2 +
        (a.z - b.z) ** 2
    )


def normalize_angle(angle):
    """
    Normalize an angle to the interval [0, 2*pi).
    
        Parameters:
            angle (float): Angle in radians.
    
        Returns:
            float: Equivalent normalized angle in radians.
    """
    two_pi = 2.0 * math.pi
    angle = angle % two_pi
    if angle < 0:
        angle += two_pi
    return angle


def angle_from_center(center, point):
    """
    Compute the polar angle of a point around a center.
    
        Parameters:
            center (adsk.core.Point3D): Circle or arc center.
            point (adsk.core.Point3D): Point located on or near the circle.
    
        Returns:
            float: Angle in radians, normalized to [0, 2*pi).
    """
    return normalize_angle(math.atan2(point.y - center.y, point.x - center.x))


def make_point_on_circle(center, radius, angle):
    """
    Create a point on a circle at a given angle.
    
        Parameters:
            center (adsk.core.Point3D): Circle center.
            radius (float): Circle radius in centimeters.
            angle (float): Angle in radians.
    
        Returns:
            adsk.core.Point3D: Point located on the circle.
    """
    return make_point3d(
        center.x + radius * math.cos(angle),
        center.y + radius * math.sin(angle),
        center.z,
    )


def normalize_dir_xy(dx, dy, settings):
    """
    Normalize a 2D direction vector and force a unique orientation.
    
        Parameters:
            dx (float): X component of the vector.
            dy (float): Y component of the vector.
            settings (CleanupSettings): Options containing the tolerance.
    
        Returns:
            tuple[float, float] | None: Normalized direction, or None for
            near-zero vectors.
    """
    length = math.sqrt(dx * dx + dy * dy)
    if length <= tol(settings):
        return None

    ux = dx / length
    uy = dy / length

    if ux < -tol(settings) or (abs(ux) <= tol(settings) and uy < -tol(settings)):
        ux = -ux
        uy = -uy

    return ux, uy


def collection_count(obj):
    """
    Safely read the count of a Fusion collection-like object.
    
        Parameters:
            obj: Fusion collection or any object exposing a count property.
    
        Returns:
            int: Collection count, or 0 if the count cannot be read.
    """
    try:
        return int(obj.count)
    except:
        return 0


def safe_count_property(obj, name):
    """
    Safely read a collection count from an object property.
    
        Parameters:
            obj: Object that may contain the requested property.
            name (str): Property name to read.
    
        Returns:
            int: Count of the property collection, or 0 when unavailable.
    """
    try:
        return collection_count(getattr(obj, name))
    except:
        return 0


def safe_bool_property(obj, name, default=False):
    """
    Safely read a boolean property from an object.
    
        Parameters:
            obj: Object that may contain the requested property.
            name (str): Property name to read.
            default (bool): Value returned when the property is missing.
    
        Returns:
            bool: Property value or the provided default.
    """
    try:
        return bool(getattr(obj, name))
    except:
        return default


def is_reference_or_linked(curve):
    """
    Check whether a curve is projected, referenced or linked.
    
        Parameters:
            curve: Fusion sketch curve to inspect.
    
        Returns:
            bool: True when the curve appears to be reference/projection geometry.
    """
    try:
        if curve.isReference:
            return True
    except:
        pass

    try:
        if curve.isLinked:
            return True
    except:
        pass

    return False


def is_deletable_candidate(curve, settings, plan=None):
    """
    Check whether a curve may be modified by the cleanup plan.
    
        The check includes Fusion validity, deletability, and the user option that
        protects projected/reference geometry.
    
        Parameters:
            curve: Fusion sketch curve to test.
            settings (CleanupSettings): User-selected cleanup options.
            plan (CleanupPlan | None): Optional plan used to increment skip counters.
    
        Returns:
            bool: True when the curve can be considered for deletion/replacement.
    """
    try:
        if not curve.isValid:
            return False
    except:
        pass

    if is_reference_or_linked(curve) and not settings.allow_reference_geometry:
        if plan:
            plan.protected_skipped += 1
        return False

    try:
        if not curve.isDeletable:
            return False
    except:
        pass

    return True


def curve_has_constraints_or_dimensions(curve):
    """
    Check whether a curve has dimensions, constraints or fixed state.
    
        Parameters:
            curve: Fusion sketch curve to inspect.
    
        Returns:
            bool: True when dimensions, geometric constraints or fixed state exist.
    """
    return (
        safe_count_property(curve, "sketchDimensions") > 0
        or safe_count_property(curve, "geometricConstraints") > 0
        or safe_bool_property(curve, "isFixed", False)
    )


def group_has_constraints_or_dimensions(curves):
    """
    Check whether any curve in a group is constrained or dimensioned.
    
        Parameters:
            curves (list): Fusion sketch curves in one merge group.
    
        Returns:
            bool: True when at least one curve is constrained or dimensioned.
    """
    return any(curve_has_constraints_or_dimensions(c) for c in curves)


def construction_key(curve, settings):
    """
    Return the construction-normal grouping key for a curve.
    
        Parameters:
            curve: Fusion sketch curve.
            settings (CleanupSettings): Options controlling construction handling.
    
        Returns:
            bool | str: Construction state, or a shared key when construction and
            normal geometry are allowed to merge together.
    """
    if settings.merge_construction_and_normal:
        return "mixed"
    try:
        return bool(curve.isConstruction)
    except:
        return False


def resulting_construction_state(curves):
    """If any source is normal geometry, create normal geometry; otherwise construction."""
    any_normal = False
    any_construction = False

    for c in curves:
        try:
            if c.isConstruction:
                any_construction = True
            else:
                any_normal = True
        except:
            any_normal = True

    if any_normal:
        return False
    return any_construction


def keep_score(curve):
    """Prefer keeping constrained/dimensioned curves when deleting exact duplicates."""
    score = 0
    score += safe_count_property(curve, "sketchDimensions") * 1000
    score += safe_count_property(curve, "geometricConstraints") * 100
    if safe_bool_property(curve, "isFixed", False):
        score += 20
    if safe_bool_property(curve, "isConstruction", False):
        score += 1
    return score


def delete_curve(curve):
    """
    Delete a Fusion sketch curve safely.
    
        Parameters:
            curve: Fusion sketch curve to delete.
    
        Returns:
            bool: True when Fusion reports successful deletion, False otherwise.
    """
    try:
        if curve.isValid:
            return bool(curve.deleteMe())
    except:
        pass
    return False


# -----------------------------------------------------------------------------
# Curve signatures for exact duplicates
# -----------------------------------------------------------------------------

def line_signature(line, settings):
    """
    Build a duplicate-detection signature for a sketch line.
    
        Parameters:
            line (adsk.fusion.SketchLine): Line to describe.
            settings (CleanupSettings): Tolerance and grouping options.
    
        Returns:
            tuple: Hashable signature independent of line direction.
    """
    p1 = line.startSketchPoint.geometry
    p2 = line.endSketchPoint.geometry

    a = qpt(p1, settings)
    b = qpt(p2, settings)

    if b < a:
        a, b = b, a

    return ("LINE", construction_key(line, settings), a, b)


def circle_signature(circle, settings):
    """
    Build a duplicate-detection signature for a sketch circle.
    
        Parameters:
            circle (adsk.fusion.SketchCircle): Circle to describe.
            settings (CleanupSettings): Tolerance and grouping options.
    
        Returns:
            tuple: Hashable signature using center and radius.
    """
    center = circle.centerSketchPoint.geometry
    return ("CIRCLE", construction_key(circle, settings), qpt(center, settings), q(circle.radius, settings))


def arc_signature(arc, settings):
    """
    Build a duplicate-detection signature for a circular arc.
    
        Parameters:
            arc (adsk.fusion.SketchArc): Arc to describe.
            settings (CleanupSettings): Tolerance and grouping options.
    
        Returns:
            tuple: Hashable signature using center, radius, endpoints and length.
    """
    center = arc.centerSketchPoint.geometry
    start = arc.startSketchPoint.geometry
    end = arc.endSketchPoint.geometry

    a = qpt(start, settings)
    b = qpt(end, settings)
    if b < a:
        a, b = b, a

    radius = q(dist(center, start), settings)
    length = q(getattr(arc, "length", 0.0), settings)

    return ("ARC", construction_key(arc, settings), qpt(center, settings), radius, a, b, length)


def ellipse_signature(ellipse, settings):
    """
    Build a duplicate-detection signature for an ellipse.
    
        Parameters:
            ellipse (adsk.fusion.SketchEllipse): Ellipse to describe.
            settings (CleanupSettings): Tolerance and grouping options.
    
        Returns:
            tuple: Hashable signature using center, axis and radii.
    """
    center = ellipse.centerSketchPoint.geometry
    axis = ellipse.majorAxis

    ax = q(axis.x, settings)
    ay = q(axis.y, settings)
    az = q(axis.z, settings)

    if (ax, ay, az) < (0, 0, 0):
        ax, ay, az = -ax, -ay, -az

    return (
        "ELLIPSE",
        construction_key(ellipse, settings),
        qpt(center, settings),
        ax,
        ay,
        az,
        q(ellipse.majorAxisRadius, settings),
        q(ellipse.minorAxisRadius, settings),
    )


def elliptical_arc_signature(arc, settings):
    """
    Build a duplicate-detection signature for an elliptical arc.
    
        Parameters:
            arc (adsk.fusion.SketchEllipticalArc): Elliptical arc to describe.
            settings (CleanupSettings): Tolerance and grouping options.
    
        Returns:
            tuple: Hashable signature using center, axis, radii, endpoints and length.
    """
    center = arc.centerSketchPoint.geometry
    start = arc.startSketchPoint.geometry
    end = arc.endSketchPoint.geometry

    a = qpt(start, settings)
    b = qpt(end, settings)
    if b < a:
        a, b = b, a

    axis = arc.majorAxis
    ax = q(axis.x, settings)
    ay = q(axis.y, settings)
    az = q(axis.z, settings)

    if (ax, ay, az) < (0, 0, 0):
        ax, ay, az = -ax, -ay, -az

    return (
        "ELLIPTICAL_ARC",
        construction_key(arc, settings),
        qpt(center, settings),
        ax,
        ay,
        az,
        q(arc.majorAxisRadius, settings),
        q(arc.minorAxisRadius, settings),
        a,
        b,
        q(getattr(arc, "length", 0.0), settings),
    )


def fitted_spline_signature(spline, settings):
    """
    Build an approximate duplicate signature for a fitted spline.
    
        Parameters:
            spline (adsk.fusion.SketchFittedSpline): Fitted spline to describe.
            settings (CleanupSettings): Tolerance and grouping options.
    
        Returns:
            tuple | None: Hashable signature based on fit points when available,
            otherwise a bounding-box fallback. None when no reliable data exists.
    """
    points = []

    try:
        fit_points = spline.fitPoints
        for i in range(fit_points.count):
            points.append(qpt(fit_points.item(i).geometry, settings))
    except:
        points = []

    if not points:
        try:
            bb = spline.boundingBox
            return (
                "SPLINE_FALLBACK",
                construction_key(spline, settings),
                qpt(bb.minPoint, settings),
                qpt(bb.maxPoint, settings),
                q(getattr(spline, "length", 0.0), settings),
            )
        except:
            return None

    reversed_points = list(reversed(points))
    if tuple(reversed_points) < tuple(points):
        points = reversed_points

    return ("FITTED_SPLINE", construction_key(spline, settings), tuple(points), q(getattr(spline, "length", 0.0), settings))


def generic_curve_signature(curve, settings):
    """
    Build a fallback duplicate signature for unsupported curve types.
    
        Parameters:
            curve: Fusion sketch curve not handled by a specialized signature.
            settings (CleanupSettings): Tolerance and grouping options.
    
        Returns:
            tuple | None: Bounding-box-based signature, or None on failure.
    """
    try:
        bb = curve.boundingBox
        return (
            "GENERIC",
            curve.objectType,
            construction_key(curve, settings),
            qpt(bb.minPoint, settings),
            qpt(bb.maxPoint, settings),
            q(getattr(curve, "length", 0.0), settings),
        )
    except:
        return None


def curve_signature(curve, settings):
    """
    Dispatch a sketch curve to the correct signature builder.
    
        Parameters:
            curve: Fusion sketch curve.
            settings (CleanupSettings): Tolerance and grouping options.
    
        Returns:
            tuple | None: Hashable duplicate-detection signature.
    """
    try:
        ot = curve.objectType

        line_like = line_like_segment_from_curve(curve, settings)
        if line_like:
            start, end, is_spline = line_like
            return line_like_signature(curve, start, end, is_spline, settings)

        if is_supported_spline_curve(curve):
            # Dense SVG imports may contain thousands of splines. Non-straight
            # splines are skipped by default to keep Test responsive.
            return None

        if ot == adsk.fusion.SketchCircle.classType():
            return circle_signature(curve, settings)
        if ot == adsk.fusion.SketchArc.classType():
            return arc_signature(curve, settings)
        if ot == adsk.fusion.SketchEllipse.classType():
            return ellipse_signature(curve, settings)
        if ot == adsk.fusion.SketchEllipticalArc.classType():
            return elliptical_arc_signature(curve, settings)
        if ot == adsk.fusion.SketchFittedSpline.classType():
            return fitted_spline_signature(curve, settings)

        return generic_curve_signature(curve, settings)

    except:
        return None


def all_supported_curves(sketch):
    """
    Collect sketch curves supported by the cleaner.
    
        Parameters:
            sketch (adsk.fusion.Sketch): Sketch to inspect.
    
        Returns:
            list: Curves from common sketch curve collections.
    """
    curves = []
    sc = sketch.sketchCurves

    collections = [
        "sketchLines",
        "sketchArcs",
        "sketchCircles",
        "sketchEllipses",
        "sketchEllipticalArcs",
        "sketchFittedSplines",
        "sketchControlPointSplines",
    ]

    for name in collections:
        try:
            col = getattr(sc, name)
            for i in range(col.count):
                curves.append(col.item(i))
        except:
            pass

    return curves



# -----------------------------------------------------------------------------
# SVG/imported near-straight spline support
# -----------------------------------------------------------------------------

def object_type_matches(curve, fusion_class_name):
    """
    Check a Fusion sketch curve object type without failing on older APIs.

    Parameters:
        curve: Fusion sketch curve.
        fusion_class_name (str): Class name in adsk.fusion, for example
            "SketchFittedSpline".

    Returns:
        bool: True when the curve objectType matches the requested class.
    """
    try:
        cls = getattr(adsk.fusion, fusion_class_name)
        return curve.objectType == cls.classType()
    except:
        return False


def is_supported_spline_curve(curve):
    """
    Check whether a curve is a fitted or control-point spline.

    SVG imports can represent visually straight segments as splines. This helper
    identifies the spline types that the add-in can inspect.

    Parameters:
        curve: Fusion sketch curve.

    Returns:
        bool: True for fitted or control-point splines.
    """
    return (
        object_type_matches(curve, "SketchFittedSpline")
        or object_type_matches(curve, "SketchControlPointSpline")
    )


def safe_sketch_point_geometry(obj, attr_name):
    """
    Read a SketchPoint geometry property safely.

    Parameters:
        obj: Fusion object containing a sketch point attribute.
        attr_name (str): Name such as "startSketchPoint" or "endSketchPoint".

    Returns:
        adsk.core.Point3D | None: Point geometry, or None.
    """
    try:
        sketch_point = getattr(obj, attr_name)
        if sketch_point:
            return sketch_point.geometry
    except:
        pass
    return None


def append_unique_point(points, point, settings):
    """
    Append a point only if it is not already present within tolerance.

    Parameters:
        points (list): List of Point3D objects.
        point (adsk.core.Point3D | None): Point to append.
        settings (CleanupSettings): Active tolerance settings.

    Returns:
        None.
    """
    if not point:
        return

    key = qpt(point, settings)
    for existing in points:
        if qpt(existing, settings) == key:
            return

    points.append(point)


def collection_points(collection, settings):
    """
    Extract point geometries from a Fusion collection.

    Parameters:
        collection: Fusion collection containing SketchPoint-like objects.
        settings (CleanupSettings): Active tolerance settings.

    Returns:
        list[adsk.core.Point3D]: Extracted unique points.
    """
    points = []

    try:
        for i in range(min(collection.count, MAX_SPLINE_DEFINITION_POINTS)):
            item = collection.item(i)

            try:
                append_unique_point(points, item.geometry, settings)
                continue
            except:
                pass

            try:
                append_unique_point(points, item, settings)
            except:
                pass
    except:
        pass

    return points


def spline_definition_points(curve, settings):
    """
    Collect points that define an imported spline.

    The function tries several API properties because SVG/imported geometry may
    become either fitted splines or control-point splines, depending on Fusion
    version and import content.

    Parameters:
        curve: Fusion sketch spline.
        settings (CleanupSettings): Active tolerance settings.

    Returns:
        list[adsk.core.Point3D]: Unique points describing the spline.
    """
    points = []

    append_unique_point(points, safe_sketch_point_geometry(curve, "startSketchPoint"), settings)

    for attr_name in ("fitPoints", "controlPoints"):
        try:
            for p in collection_points(getattr(curve, attr_name), settings):
                append_unique_point(points, p, settings)
        except:
            pass

    # Do not inspect controlFrameLines here. On dense SVG imports this can be
    # very expensive and can make Fusion look as if it is looping.

    append_unique_point(points, safe_sketch_point_geometry(curve, "endSketchPoint"), settings)

    return points


def point_line_distance_xy(point, start, end):
    """
    Compute the 2D perpendicular distance from a point to a line.

    Parameters:
        point (adsk.core.Point3D): Point to test.
        start (adsk.core.Point3D): Line start.
        end (adsk.core.Point3D): Line end.

    Returns:
        float: Perpendicular distance in centimeters.
    """
    dx = end.x - start.x
    dy = end.y - start.y
    length = math.sqrt(dx * dx + dy * dy)

    if length <= 1e-12:
        return dist(point, start)

    return abs((point.x - start.x) * dy - (point.y - start.y) * dx) / length


def projected_parameter_on_segment(point, start, end):
    """
    Project a point on a finite segment and return its normalized parameter.

    Parameters:
        point (adsk.core.Point3D): Point to project.
        start (adsk.core.Point3D): Segment start.
        end (adsk.core.Point3D): Segment end.

    Returns:
        float: Parameter where 0 is start and 1 is end.
    """
    dx = end.x - start.x
    dy = end.y - start.y
    denom = dx * dx + dy * dy

    if denom <= 1e-24:
        return 0.0

    return ((point.x - start.x) * dx + (point.y - start.y) * dy) / denom


def near_straight_spline_as_line_segment(curve, settings):
    """
    Convert a near-straight imported spline to a virtual line segment.

    The spline is accepted only if all available definition points are close to
    the chord from start to end, and the curve length is close to that chord.
    This is intended for SVG/DXF imports where visually straight segments are
    represented as splines.

    Parameters:
        curve: Fusion sketch spline to inspect.
        settings (CleanupSettings): Active cleanup settings.

    Returns:
        tuple[adsk.core.Point3D, adsk.core.Point3D] | None: Start/end points
        when the spline is near-straight, otherwise None.
    """
    if not getattr(settings, "treat_near_straight_splines_as_lines", False):
        return None

    if not is_supported_spline_curve(curve):
        return None

    points = spline_definition_points(curve, settings)
    if len(points) < 2:
        return None

    start = safe_sketch_point_geometry(curve, "startSketchPoint") or points[0]
    end = safe_sketch_point_geometry(curve, "endSketchPoint") or points[-1]

    chord = dist(start, end)
    if chord <= tol(settings):
        return None

    # Relative allowance keeps long SVG lines from being rejected because of
    # tiny imported numerical noise. The absolute tolerance still dominates for
    # normal CAD-size cleanup.
    straightness_tol = max(tol(settings), chord * 0.001)

    max_distance = 0.0
    min_param = 0.0
    max_param = 1.0

    for point in points:
        max_distance = max(max_distance, point_line_distance_xy(point, start, end))
        param = projected_parameter_on_segment(point, start, end)
        min_param = min(min_param, param)
        max_param = max(max_param, param)

    if max_distance > straightness_tol:
        return None

    # Reject splines whose definition points extend far beyond the endpoint chord.
    endpoint_slop = max(0.05, 3.0 * tol(settings) / chord)
    if min_param < -endpoint_slop or max_param > 1.0 + endpoint_slop:
        return None

    # Do not call curve.length here: it can be slow on thousands of SVG splines.

    return (start, end)


def line_like_segment_from_curve(curve, settings):
    """
    Return a line-like segment for SketchLine or near-straight imported spline.

    Parameters:
        curve: Fusion sketch curve.
        settings (CleanupSettings): Active cleanup settings.

    Returns:
        tuple[adsk.core.Point3D, adsk.core.Point3D, bool] | None:
        start, end and a boolean indicating whether the source was a spline.
    """
    try:
        if curve.objectType == adsk.fusion.SketchLine.classType():
            return (
                curve.startSketchPoint.geometry,
                curve.endSketchPoint.geometry,
                False,
            )
    except:
        pass

    segment = near_straight_spline_as_line_segment(curve, settings)
    if segment:
        return (segment[0], segment[1], True)

    return None


def line_like_signature(curve, start, end, is_spline, settings):
    """
    Build a duplicate signature for a line-like curve.

    Parameters:
        curve: Source Fusion curve.
        start (adsk.core.Point3D): Segment start.
        end (adsk.core.Point3D): Segment end.
        is_spline (bool): True if the source was an imported spline.
        settings (CleanupSettings): Active cleanup settings.

    Returns:
        tuple: Hashable duplicate signature.
    """
    a = qpt(start, settings)
    b = qpt(end, settings)

    if b < a:
        a, b = b, a

    # Use "LINE" intentionally so a true SketchLine and a straight imported
    # spline with the same endpoints are considered duplicates.
    return ("LINE", construction_key(curve, settings), a, b)


def line_like_group_key(curve, start, end, settings):
    """
    Build a support-line grouping key for a line-like curve.

    Parameters:
        curve: Source Fusion curve.
        start (adsk.core.Point3D): Segment start.
        end (adsk.core.Point3D): Segment end.
        settings (CleanupSettings): Active cleanup settings.

    Returns:
        tuple | None: Grouping key or None for near-zero-length segments.
    """
    dx = end.x - start.x
    dy = end.y - start.y

    direction = normalize_dir_xy(dx, dy, settings)
    if direction is None:
        return None

    ux, uy = direction
    nx, ny = -uy, ux
    offset = start.x * nx + start.y * ny

    return (
        construction_key(curve, settings),
        q(ux, settings),
        q(uy, settings),
        q(offset, settings),
    )


# -----------------------------------------------------------------------------
# Exact duplicate planning
# -----------------------------------------------------------------------------

def plan_exact_duplicate_removal(plan):
    """
    Populate the cleanup plan with exact duplicate deletions.
    
        Parameters:
            plan (CleanupPlan): Plan to update in place.
    
        Returns:
            None.
    """
    if not plan.settings.delete_exact_duplicates:
        return

    by_sig = {}

    for curve in curves_for_exact_duplicate_scan(plan.sketch, plan.settings, plan):
        if not is_deletable_candidate(curve, plan.settings, plan):
            continue

        sig = curve_signature(curve, plan.settings)
        if sig is None:
            plan.unsupported_skipped += 1
            continue

        if sig not in by_sig:
            by_sig[sig] = curve
            continue

        kept = by_sig[sig]
        candidate = curve

        if keep_score(candidate) > keep_score(kept):
            to_delete = kept
            by_sig[sig] = candidate
        else:
            to_delete = candidate

        if to_delete not in plan.exact_duplicates_to_delete:
            plan.exact_duplicates_to_delete.append(to_delete)


# -----------------------------------------------------------------------------
# Line partial merge planning
# -----------------------------------------------------------------------------

def line_group_key(line, settings):
    """
    Build a geometric grouping key for collinear sketch lines.
    
        Parameters:
            line (adsk.fusion.SketchLine): Line to classify.
            settings (CleanupSettings): Tolerance and construction options.
    
        Returns:
            tuple | None: Key representing the infinite support line, or None
            for near-zero-length lines.
    """
    p1 = line.startSketchPoint.geometry
    p2 = line.endSketchPoint.geometry

    dx = p2.x - p1.x
    dy = p2.y - p1.y

    direction = normalize_dir_xy(dx, dy, settings)
    if direction is None:
        return None

    ux, uy = direction
    nx, ny = -uy, ux
    offset = p1.x * nx + p1.y * ny

    return (
        construction_key(line, settings),
        q(ux, settings),
        q(uy, settings),
        q(offset, settings),
    )


def projection_on_line(point, ux, uy):
    """
    Project a point onto a normalized 2D line direction.
    
        Parameters:
            point (adsk.core.Point3D): Point to project.
            ux (float): Normalized X direction.
            uy (float): Normalized Y direction.
    
        Returns:
            float: Scalar coordinate along the line.
    """
    return point.x * ux + point.y * uy


def point_from_line_projection(t_value, offset, ux, uy):
    """
    Reconstruct a point from a scalar line projection.
    
        Parameters:
            t_value (float): Scalar coordinate along the support line.
            offset (float): Signed offset of the support line from origin.
            ux (float): Normalized X direction.
            uy (float): Normalized Y direction.
    
        Returns:
            adsk.core.Point3D: Reconstructed point on the line.
    """
    nx, ny = -uy, ux
    x = t_value * ux + offset * nx
    y = t_value * uy + offset * ny
    return make_point3d(x, y, 0.0)


def merge_linear_intervals(intervals, settings):
    """
    Merge overlapping or touching intervals on one line.
    
        Parameters:
            intervals (list): Tuples of (start, end, curve) on a support line.
            settings (CleanupSettings): Tolerance controlling interval merging.
    
        Returns:
            list: Merged intervals with the source curves that contributed to each one.
    """
    intervals = sorted(intervals, key=lambda item: item[0])
    merged = []

    for t1, t2, curve in intervals:
        if not merged:
            merged.append([t1, t2, [curve]])
            continue

        last = merged[-1]
        if t1 <= last[1] + tol(settings):
            last[1] = max(last[1], t2)
            last[2].append(curve)
        else:
            merged.append([t1, t2, [curve]])

    return merged


def plan_line_merges(plan):
    """
    Find partially overlapping straight lines and plan replacements.
    
        Parameters:
            plan (CleanupPlan): Plan to update in place.
    
        Returns:
            None.
    """
    if not plan.settings.merge_partially_overlapping_lines:
        return

    sc = plan.sketch.sketchCurves
    line_like_items = []

    try:
        lines_col = sc.sketchLines
        for i in range(lines_col.count):
            line = lines_col.item(i)
            segment = line_like_segment_from_curve(line, plan.settings)
            if segment:
                start, end, is_spline = segment
                line_like_items.append((line, start, end, is_spline))
    except:
        pass

    if getattr(plan.settings, "treat_near_straight_splines_as_lines", False):
        analyzed_svg_splines = 0
        for collection_name in ("sketchFittedSplines", "sketchControlPointSplines"):
            try:
                col = getattr(sc, collection_name)
                count = col.count

                for i in range(count):
                    if analyzed_svg_splines >= MAX_SVG_SPLINES_TO_ANALYZE:
                        plan.svg_spline_candidates_skipped += max(0, count - i)
                        break

                    spline = col.item(i)
                    analyzed_svg_splines += 1

                    segment = line_like_segment_from_curve(spline, plan.settings)
                    if segment:
                        start, end, is_spline = segment
                        line_like_items.append((spline, start, end, is_spline))
                        plan.svg_straight_spline_candidates += 1
            except:
                pass

    groups = {}

    for line, p1, p2, is_spline in line_like_items:
        if not is_deletable_candidate(line, plan.settings, plan):
            continue

        key = line_like_group_key(line, p1, p2, plan.settings)
        if key is None:
            continue

        _construction, ux_q, uy_q, offset_q = key

        ux = ux_q * tol(plan.settings)
        uy = uy_q * tol(plan.settings)
        offset = offset_q * tol(plan.settings)

        length = math.sqrt(ux * ux + uy * uy)
        if length <= tol(plan.settings):
            continue

        ux /= length
        uy /= length

        t1 = projection_on_line(p1, ux, uy)
        t2 = projection_on_line(p2, ux, uy)

        if t2 < t1:
            t1, t2 = t2, t1

        groups.setdefault(key, []).append((t1, t2, line))

    for key, intervals in groups.items():
        if len(intervals) < 2:
            continue

        source_curves = [item[2] for item in intervals]

        if group_has_constraints_or_dimensions(source_curves) and not plan.settings.allow_constrained_or_dimensioned:
            plan.constrained_groups_skipped += 1
            continue

        merged = merge_linear_intervals(intervals, plan.settings)

        if len(merged) >= len(intervals):
            continue

        _construction, ux_q, uy_q, offset_q = key

        ux = ux_q * tol(plan.settings)
        uy = uy_q * tol(plan.settings)
        offset = offset_q * tol(plan.settings)

        length = math.sqrt(ux * ux + uy * uy)
        if length <= tol(plan.settings):
            continue

        ux /= length
        uy /= length

        result_curves = []
        out_is_construction = resulting_construction_state(source_curves)

        for t1, t2, _curves in merged:
            if abs(t2 - t1) <= tol(plan.settings):
                continue

            result_curves.append({
                "type": "line",
                "start": point_from_line_projection(t1, offset, ux, uy),
                "end": point_from_line_projection(t2, offset, ux, uy),
                "isConstruction": out_is_construction,
            })

        if result_curves:
            plan.line_merge_groups.append({
                "source_curves": source_curves,
                "result_curves": result_curves,
            })


# -----------------------------------------------------------------------------
# Circular arc/circle partial merge planning
# -----------------------------------------------------------------------------

def is_circle(curve):
    """
    Check whether a curve is a Fusion sketch circle.
    
        Parameters:
            curve: Fusion sketch curve.
    
        Returns:
            bool: True for SketchCircle objects.
    """
    try:
        return curve.objectType == adsk.fusion.SketchCircle.classType()
    except:
        return False


def is_arc(curve):
    """
    Check whether a curve is a Fusion sketch arc.
    
        Parameters:
            curve: Fusion sketch curve.
    
        Returns:
            bool: True for SketchArc objects.
    """
    try:
        return curve.objectType == adsk.fusion.SketchArc.classType()
    except:
        return False


def circular_group_key(curve, settings):
    """
    Build a grouping key for circular arcs and circles.
    
        Parameters:
            curve: Fusion SketchArc or SketchCircle.
            settings (CleanupSettings): Tolerance and construction options.
    
        Returns:
            tuple | None: Key based on construction state, center and radius.
    """
    try:
        if is_circle(curve):
            center = curve.centerSketchPoint.geometry
            radius = curve.radius
        elif is_arc(curve):
            center = curve.centerSketchPoint.geometry
            start = curve.startSketchPoint.geometry
            radius = dist(center, start)
        else:
            return None
    except:
        return None

    return (
        construction_key(curve, settings),
        qpt(center, settings),
        q(radius, settings),
    )


def circle_interval():
    """
    Return the angular interval representing a full circle.
    
        Parameters:
            None.
    
        Returns:
            tuple: (start_angle, end_angle, is_full_circle).
    """
    return (0.0, 2.0 * math.pi, True)


def arc_interval(arc):
    """
    Convert a Fusion arc to an angular interval.
    
        Parameters:
            arc (adsk.fusion.SketchArc): Arc to analyze.
    
        Returns:
            tuple | None: (start_angle, end_angle, is_full_circle), or None for
            invalid arcs.
    """
    center = arc.centerSketchPoint.geometry
    start = arc.startSketchPoint.geometry
    end = arc.endSketchPoint.geometry

    radius = dist(center, start)
    if radius <= 1e-12:
        return None

    start_angle = angle_from_center(center, start)
    end_angle = angle_from_center(center, end)

    ccw_delta = normalize_angle(end_angle - start_angle)
    cw_delta = normalize_angle(start_angle - end_angle)

    # Use the sketch arc length when available to decide which side of the circle
    # is actually covered by the arc.
    try:
        sweep_abs = abs(float(arc.length)) / radius
    except:
        sweep_abs = ccw_delta

    two_pi = 2.0 * math.pi
    if sweep_abs >= two_pi - 1e-7:
        return circle_interval()

    if abs(ccw_delta - sweep_abs) <= abs(cw_delta - sweep_abs):
        return (start_angle, start_angle + ccw_delta, False)

    # Represent clockwise coverage as the equivalent CCW interval from end to start.
    return (end_angle, end_angle + cw_delta, False)


def split_circular_interval(start, end):
    """Return one or two intervals inside [0, 2*pi]."""
    two_pi = 2.0 * math.pi
    start = normalize_angle(start)
    sweep = max(0.0, end - start)

    if sweep >= two_pi - 1e-9:
        return [(0.0, two_pi)]

    raw_end = start + sweep

    if raw_end <= two_pi:
        return [(start, raw_end)]

    return [(start, two_pi), (0.0, raw_end - two_pi)]


def merge_angular_intervals(intervals, angle_tol):
    """
    Merge overlapping or touching angular intervals.
    
        Parameters:
            intervals (list): List of angular intervals in radians.
            angle_tol (float): Angular tolerance in radians.
    
        Returns:
            list: Merged angular intervals.
    """
    if not intervals:
        return []

    intervals = sorted(intervals, key=lambda item: item[0])
    merged = []

    for a1, a2 in intervals:
        if a2 - a1 <= angle_tol:
            continue

        if not merged:
            merged.append([a1, a2])
            continue

        last = merged[-1]
        if a1 <= last[1] + angle_tol:
            last[1] = max(last[1], a2)
        else:
            merged.append([a1, a2])

    # Join wrap-around intervals, e.g. [0, 0.2] and [6.0, 2*pi].
    two_pi = 2.0 * math.pi
    if len(merged) > 1:
        first = merged[0]
        last = merged[-1]

        if first[0] <= angle_tol and last[1] >= two_pi - angle_tol:
            joined = [last[0], first[1] + two_pi]
            middle = merged[1:-1]
            merged = [joined] + middle

    return merged


def detect_interval_overlap_or_touch(intervals, angle_tol):
    """
    Detect whether angular intervals overlap or touch.
    
        Parameters:
            intervals (list): Angular intervals inside [0, 2*pi].
            angle_tol (float): Angular tolerance in radians.
    
        Returns:
            bool: True when at least two intervals overlap or touch.
    """
    if len(intervals) < 2:
        return False

    sorted_intervals = sorted(intervals, key=lambda item: item[0])
    previous_end = sorted_intervals[0][1]

    for a1, a2 in sorted_intervals[1:]:
        if a1 <= previous_end + angle_tol:
            return True
        previous_end = max(previous_end, a2)

    # Wrap-around overlap/touch.
    two_pi = 2.0 * math.pi
    if sorted_intervals[0][0] <= angle_tol and sorted_intervals[-1][1] >= two_pi - angle_tol:
        return True

    return False


def plan_circular_merges(plan):
    """
    Find overlapping arcs/circles and plan circular replacements.
    
        Parameters:
            plan (CleanupPlan): Plan to update in place.
    
        Returns:
            None.
    """
    if not plan.settings.merge_partially_overlapping_circular_curves:
        return

    curves = []
    try:
        arcs = plan.sketch.sketchCurves.sketchArcs
        for i in range(arcs.count):
            curves.append(arcs.item(i))
    except:
        pass

    try:
        circles = plan.sketch.sketchCurves.sketchCircles
        for i in range(circles.count):
            curves.append(circles.item(i))
    except:
        pass

    groups = {}

    for curve in curves:
        if not is_deletable_candidate(curve, plan.settings, plan):
            continue

        key = circular_group_key(curve, plan.settings)
        if key is None:
            continue

        if is_circle(curve):
            interval = circle_interval()
        elif is_arc(curve):
            interval = arc_interval(curve)
        else:
            continue

        if interval is None:
            continue

        groups.setdefault(key, []).append((curve, interval))

    for key, items in groups.items():
        if len(items) < 2:
            continue

        source_curves = [item[0] for item in items]

        if group_has_constraints_or_dimensions(source_curves) and not plan.settings.allow_constrained_or_dimensioned:
            plan.constrained_groups_skipped += 1
            continue

        _construction, center_key, radius_key = key
        # Use the first source curve as geometric reference to avoid reconstructing
        # center/radius only from quantized values.
        sample = source_curves[0]

        if is_circle(sample):
            center = sample.centerSketchPoint.geometry
            radius = sample.radius
        else:
            center = sample.centerSketchPoint.geometry
            radius = dist(center, sample.startSketchPoint.geometry)

        angle_tol = max(1e-8, tol(plan.settings) / max(radius, tol(plan.settings)))

        split_intervals = []
        has_full_circle = False

        for _curve, interval in items:
            start, end, full = interval
            if full:
                has_full_circle = True
                split_intervals.append((0.0, 2.0 * math.pi))
            else:
                split_intervals.extend(split_circular_interval(start, end))

        has_overlap = has_full_circle or detect_interval_overlap_or_touch(split_intervals, angle_tol)
        merged = merge_angular_intervals(split_intervals, angle_tol)

        if not has_overlap and len(merged) >= len(items):
            continue

        out_is_construction = resulting_construction_state(source_curves)
        result_curves = []

        # If coverage is complete, create one circle.
        total_coverage = sum(max(0.0, b - a) for a, b in merged)
        if total_coverage >= 2.0 * math.pi - angle_tol:
            result_curves.append({
                "type": "circle",
                "center": make_point3d(center.x, center.y, center.z),
                "radius": radius,
                "isConstruction": out_is_construction,
            })
        else:
            for a1, a2 in merged:
                sweep = a2 - a1
                if sweep <= angle_tol:
                    continue

                # If the interval wraps beyond 2*pi, keep the sweep as-is; Fusion
                # accepts a positive sweep angle from the start point.
                start_angle = normalize_angle(a1)
                start_point = make_point_on_circle(center, radius, start_angle)

                result_curves.append({
                    "type": "arc",
                    "center": make_point3d(center.x, center.y, center.z),
                    "start": start_point,
                    "sweep": sweep,
                    "isConstruction": out_is_construction,
                })

        if result_curves:
            plan.circular_merge_groups.append({
                "source_curves": source_curves,
                "result_curves": result_curves,
            })


# -----------------------------------------------------------------------------
# Plan creation and application
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Large sketch / SVG safety guard
# -----------------------------------------------------------------------------

def safe_collection_count(sketch_curves, collection_name):
    """
    Return a sketch curve collection count without materializing curve objects.

    Parameters:
        sketch_curves: Fusion sketch.sketchCurves object.
        collection_name (str): Collection property name.

    Returns:
        int: Collection count, or 0 if unavailable.
    """
    try:
        col = getattr(sketch_curves, collection_name)
        return int(col.count)
    except:
        return 0


def sketch_curve_counts(sketch):
    """
    Count sketch curve collections without retrieving every entity.

    This is intentionally much cheaper than iterating over all curves and is used
    before Test/Apply to avoid making Fusion look as if it is looping on dense
    imported SVG sketches.

    Parameters:
        sketch (adsk.fusion.Sketch): Sketch to inspect.

    Returns:
        dict: Counts by collection name plus total, line and spline totals.
    """
    sc = sketch.sketchCurves

    counts = {
        "sketchLines": safe_collection_count(sc, "sketchLines"),
        "sketchArcs": safe_collection_count(sc, "sketchArcs"),
        "sketchCircles": safe_collection_count(sc, "sketchCircles"),
        "sketchEllipses": safe_collection_count(sc, "sketchEllipses"),
        "sketchEllipticalArcs": safe_collection_count(sc, "sketchEllipticalArcs"),
        "sketchFittedSplines": safe_collection_count(sc, "sketchFittedSplines"),
        "sketchControlPointSplines": safe_collection_count(sc, "sketchControlPointSplines"),
    }

    counts["lines"] = counts["sketchLines"]
    counts["splines"] = counts["sketchFittedSplines"] + counts["sketchControlPointSplines"]
    counts["total"] = sum(
        counts[name]
        for name in (
            "sketchLines",
            "sketchArcs",
            "sketchCircles",
            "sketchEllipses",
            "sketchEllipticalArcs",
            "sketchFittedSplines",
            "sketchControlPointSplines",
        )
    )

    return counts



def active_curve_count_for_settings(counts, settings):
    """
    Count only the curve families that the current settings can actually analyze.

    Dense imported SVG sketches can contain many splines. If SVG spline analysis
    is disabled, those splines should not make safe mode block normal cleanup of
    ordinary sketch lines, arcs or circles.
    """
    if getattr(settings, "selected_geometry_only", False):
        return 0

    if getattr(settings, "line_only_fast_mode", False):
        active = counts.get("sketchLines", 0)
        if getattr(settings, "treat_near_straight_splines_as_lines", False):
            active += counts.get("sketchFittedSplines", 0)
            active += counts.get("sketchControlPointSplines", 0)
        return active

    active = (
        counts.get("sketchLines", 0)
        + counts.get("sketchArcs", 0)
        + counts.get("sketchCircles", 0)
        + counts.get("sketchEllipses", 0)
        + counts.get("sketchEllipticalArcs", 0)
    )

    if getattr(settings, "treat_near_straight_splines_as_lines", False):
        active += counts.get("sketchFittedSplines", 0)
        active += counts.get("sketchControlPointSplines", 0)

    return active


def ignored_spline_count_for_settings(counts, settings):
    """
    Count spline/SVG entities ignored by the current settings.
    """
    if getattr(settings, "treat_near_straight_splines_as_lines", False):
        return 0

    return counts.get("sketchFittedSplines", 0) + counts.get("sketchControlPointSplines", 0)


def format_sketch_counts(counts):
    """
    Format sketch curve counts for the command summary.

    Parameters:
        counts (dict): Result of sketch_curve_counts.

    Returns:
        str: Multiline count summary.
    """
    return "\n".join([
        "Total curves: {}".format(counts.get("total", 0)),
        "Lines: {}".format(counts.get("sketchLines", 0)),
        "Arcs: {}".format(counts.get("sketchArcs", 0)),
        "Circles: {}".format(counts.get("sketchCircles", 0)),
        "Ellipses: {}".format(counts.get("sketchEllipses", 0)),
        "Elliptical arcs: {}".format(counts.get("sketchEllipticalArcs", 0)),
        "Fitted splines: {}".format(counts.get("sketchFittedSplines", 0)),
        "Control-point splines: {}".format(counts.get("sketchControlPointSplines", 0)),
    ])



def large_sketch_guard_message(sketch, settings):
    """
    Return a safe-mode blocking message when the active analyzable subset is too dense.

    Dense SVG/spline geometry is not counted as blocking when SVG spline
    analysis is disabled. This lets ordinary duplicated sketch entities be
    cleaned even when they coexist with a large imported SVG in the same sketch.
    """
    counts = sketch_curve_counts(sketch)
    active_count = active_curve_count_for_settings(counts, settings)
    ignored_splines = ignored_spline_count_for_settings(counts, settings)

    if getattr(settings, "allow_large_sketch_analysis", False):
        return None

    reasons = []

    if active_count > MAX_SAFE_TOTAL_CURVES:
        reasons.append(
            "active analyzable curves {} > safe limit {}".format(active_count, MAX_SAFE_TOTAL_CURVES)
        )

    if counts["lines"] > MAX_SAFE_LINES:
        reasons.append(
            "lines {} > safe limit {}".format(counts["lines"], MAX_SAFE_LINES)
        )

    if getattr(settings, "treat_near_straight_splines_as_lines", False) and counts["splines"] > MAX_SAFE_SPLINES:
        reasons.append(
            "active splines {} > safe limit {}".format(counts["splines"], MAX_SAFE_SPLINES)
        )

    if not reasons:
        return None

    message = []
    message.append(tr("large_blocked_title"))
    message.append("")
    message.append(tr("large_blocked_hint"))
    message.append("")
    message.append(tr("svg_warning"))
    message.append("")
    message.append(tr("mixed_svg_note"))
    message.append("")
    message.append("Reason:")
    for reason in reasons:
        message.append("- " + reason)
    message.append("")
    message.append("Active analyzable curves: {}".format(active_count))
    message.append("Ignored SVG/spline curves: {}".format(ignored_splines))
    message.append("")
    message.append(format_sketch_counts(counts))
    message.append("")
    message.append(
        "Recommended first step: leave SVG spline analysis disabled to clean "
        "standard sketch geometry first, then handle SVG geometry separately."
    )

    return "\n".join(message)

def curves_for_exact_duplicate_scan(sketch, settings, plan=None):
    """
    Yield only curve collections that are safe and useful for exact duplicates.

    Dense SVG imports often contain thousands of splines. When SVG spline mode is
    disabled, splines are deliberately skipped instead of being materialized and
    inspected one by one.

    Parameters:
        sketch (adsk.fusion.Sketch): Sketch to scan.
        settings (CleanupSettings): Cleanup settings.
        plan (CleanupPlan | None): Optional plan used for skipped counters.

    Yields:
        Fusion sketch curve objects.
    """
    sc = sketch.sketchCurves

    collections = [
        "sketchLines",
        "sketchArcs",
        "sketchCircles",
        "sketchEllipses",
        "sketchEllipticalArcs",
    ]

    if getattr(settings, "treat_near_straight_splines_as_lines", False):
        collections.extend(["sketchFittedSplines", "sketchControlPointSplines"])
    else:
        try:
            if plan:
                plan.unsupported_skipped += (
                    safe_collection_count(sc, "sketchFittedSplines")
                    + safe_collection_count(sc, "sketchControlPointSplines")
                )
        except:
            pass

    for name in collections:
        try:
            col = getattr(sc, name)
            for i in range(col.count):
                yield col.item(i)
        except:
            pass


def build_cleanup_plan(sketch, settings):
    """
    Analyze a sketch and build a complete cleanup plan.
    
        Parameters:
            sketch (adsk.fusion.Sketch): Sketch to analyze.
            settings (CleanupSettings): User-selected cleanup options.
    
        Returns:
            CleanupPlan: Planned changes for preview or application.
    """
    plan = CleanupPlan(sketch, settings)
    plan_exact_duplicate_removal(plan)
    plan_line_merges(plan)
    plan_circular_merges(plan)
    return plan


def add_result_curve_to_sketch(sketch, result):
    """
    Create one replacement curve in a sketch.
    
        Parameters:
            sketch (adsk.fusion.Sketch): Destination sketch.
            result (dict): Result-curve descriptor generated by a cleanup plan.
    
        Returns:
            object | None: Created Fusion curve, or None if creation fails.
    """
    try:
        if result["type"] == "line":
            curve = sketch.sketchCurves.sketchLines.addByTwoPoints(result["start"], result["end"])
        elif result["type"] == "circle":
            curve = sketch.sketchCurves.sketchCircles.addByCenterRadius(result["center"], result["radius"])
        elif result["type"] == "arc":
            curve = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(result["center"], result["start"], result["sweep"])
        else:
            return None

        try:
            curve.isConstruction = bool(result.get("isConstruction", False))
        except:
            pass

        return curve

    except:
        return None


def apply_cleanup_plan(plan):
    """
    Apply a cleanup plan to the target sketch.
    
        Parameters:
            plan (CleanupPlan): Planned deletions and replacement curves.
    
        Returns:
            tuple[int, int]: Number of deleted/replaced curves and number of
            created replacement curves.
    """
    sketch = plan.sketch
    old_deferred = False

    try:
        old_deferred = sketch.isComputeDeferred
        sketch.isComputeDeferred = True
    except:
        pass

    deleted = 0
    created = 0

    try:
        # Apply replacement groups first. Exact duplicates that are part of a
        # replacement group may become invalid; delete_curve handles that safely.
        for group in plan.line_merge_groups + plan.circular_merge_groups:
            for curve in group["source_curves"]:
                if delete_curve(curve):
                    deleted += 1

            for result in group["result_curves"]:
                if add_result_curve_to_sketch(sketch, result):
                    created += 1

        # Delete remaining exact duplicates.
        for curve in plan.exact_duplicates_to_delete:
            if delete_curve(curve):
                deleted += 1

    finally:
        try:
            sketch.isComputeDeferred = old_deferred
        except:
            pass

    return deleted, created


# -----------------------------------------------------------------------------
# Preview handling
# -----------------------------------------------------------------------------

def get_parent_component(sketch):
    """
    Return the Fusion component owning a sketch.
    
        Parameters:
            sketch (adsk.fusion.Sketch): Sketch whose parent component is needed.
    
        Returns:
            adsk.fusion.Component | None: Parent component, or root component as
            fallback when available.
    """
    try:
        return sketch.parentComponent
    except:
        pass

    try:
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        return design.rootComponent
    except:
        return None


def delete_preview_sketch(sketch):
    """
    Delete existing temporary preview sketches.
    
        Parameters:
            sketch (adsk.fusion.Sketch): Target sketch used to find the parent
                component containing preview sketches.
    
        Returns:
            None.
    """
    comp = get_parent_component(sketch)
    if not comp:
        return

    try:
        sketches = comp.sketches
        to_delete = []
        for i in range(sketches.count):
            s = sketches.item(i)
            try:
                if s.name == PREVIEW_SKETCH_NAME:
                    to_delete.append(s)
            except:
                pass

        for s in to_delete:
            try:
                s.deleteMe()
            except:
                pass
    except:
        pass


def create_preview_sketch(plan):
    """
    Create a temporary sketch showing planned replacement geometry.
    
        Parameters:
            plan (CleanupPlan): Cleanup plan containing replacement curves.
    
        Returns:
            adsk.fusion.Sketch | None: Created preview sketch, or None on failure.
    """
    sketch = plan.sketch
    comp = get_parent_component(sketch)
    if not comp:
        return None

    delete_preview_sketch(sketch)

    try:
        ref = sketch.referencePlane
    except:
        ref = None

    if not ref:
        return None

    preview = None

    try:
        preview = comp.sketches.add(ref)
        preview.name = PREVIEW_SKETCH_NAME

        try:
            preview.isComputeDeferred = True
        except:
            pass

        for group in plan.line_merge_groups + plan.circular_merge_groups:
            for result in group["result_curves"]:
                curve = add_result_curve_to_sketch(preview, result)
                if curve:
                    try:
                        curve.isConstruction = True
                    except:
                        pass

        try:
            preview.isComputeDeferred = False
        except:
            pass

        return preview

    except:
        try:
            if preview:
                preview.deleteMe()
        except:
            pass
        return None


def select_curves_for_preview(ui, curves):
    """
    Select curves that would be deleted or replaced.
    
        Parameters:
            ui (adsk.core.UserInterface): Fusion user interface object.
            curves (list): Fusion sketch curves to select.
    
        Returns:
            int: Number of curves successfully selected.
    """
    try:
        ui.activeSelections.clear()
    except:
        pass

    selected = 0
    for curve in curves:
        if selected >= MAX_PREVIEW_SELECTIONS:
            break

        try:
            if curve and curve.isValid:
                ui.activeSelections.add(curve)
                selected += 1
        except:
            pass

    return selected


# -----------------------------------------------------------------------------
# Target sketch and summaries
# -----------------------------------------------------------------------------

def get_target_sketch(app, ui):
    """
    Find the sketch targeted by the command.
    
        The active edit sketch is preferred. If none exists, the function tries the
        current selection and the parent sketch of a selected curve.
    
        Parameters:
            app (adsk.core.Application): Fusion application object.
            ui (adsk.core.UserInterface): Fusion user interface object.
    
        Returns:
            adsk.fusion.Sketch | None: Target sketch or None if not found.
    """
    try:
        active = app.activeEditObject
        if active and active.objectType == adsk.fusion.Sketch.classType():
            return adsk.fusion.Sketch.cast(active)
    except:
        pass

    try:
        selections = ui.activeSelections

        if selections.count > 0:
            entity = selections.item(0).entity

            sketch = adsk.fusion.Sketch.cast(entity)
            if sketch:
                return sketch

            try:
                parent = entity.parentSketch
                if parent:
                    return adsk.fusion.Sketch.cast(parent)
            except:
                pass
    except:
        pass

    return None


def line_count_to_delete(plan):
    """
    Count line curves planned for replacement.
    
        Parameters:
            plan (CleanupPlan): Cleanup plan to summarize.
    
        Returns:
            int: Number of source line curves to delete/replace.
    """
    return sum(len(g["source_curves"]) for g in plan.line_merge_groups)


def line_count_to_create(plan):
    """
    Count replacement line curves planned for creation.
    
        Parameters:
            plan (CleanupPlan): Cleanup plan to summarize.
    
        Returns:
            int: Number of replacement line curves.
    """
    return sum(len(g["result_curves"]) for g in plan.line_merge_groups)


def circular_count_to_delete(plan):
    """
    Count circular curves planned for replacement.
    
        Parameters:
            plan (CleanupPlan): Cleanup plan to summarize.
    
        Returns:
            int: Number of source arcs/circles to delete/replace.
    """
    return sum(len(g["source_curves"]) for g in plan.circular_merge_groups)


def circular_count_to_create(plan):
    """
    Count replacement circular curves planned for creation.
    
        Parameters:
            plan (CleanupPlan): Cleanup plan to summarize.
    
        Returns:
            int: Number of replacement arcs/circles.
    """
    return sum(len(g["result_curves"]) for g in plan.circular_merge_groups)



def preview_replacement_curve_count(plan):
    """
    Count replacement curves that would be drawn for preview.

    Parameters:
        plan (CleanupPlan): Cleanup plan.

    Returns:
        int: Number of replacement curves in the plan.
    """
    return line_count_to_create(plan) + circular_count_to_create(plan)


def build_summary(plan, title=None):
    """
    Build a localized text summary of a cleanup plan.
    
        Parameters:
            plan (CleanupPlan): Plan to summarize.
            title (str | None): Optional heading displayed before the summary.
    
        Returns:
            str: Human-readable localized summary text.
    """
    if title is None:
        title = ""

    total_delete = len(plan.all_curves_to_delete_or_replace())

    lines = []
    if title:
        lines.append(title)
        lines.append("")

    lines.append("{}: {}".format(tr("version_label"), ADDIN_VERSION))
    lines.append("{}: {}".format(tr("result_sketch"), plan.sketch.name))
    lines.append("{}: {}".format(tr("result_active_count"), plan.active_guard_curve_count))
    lines.append("{}: {}".format(tr("result_ignored_splines"), plan.ignored_splines_due_to_svg_disabled))
    lines.append("{}: {}".format(tr("result_selected_only"), "yes" if getattr(plan.settings, "selected_geometry_only", False) else "no"))
    lines.append("{}: {}".format(tr("result_line_only_fast"), "yes" if getattr(plan.settings, "line_only_fast_mode", False) else "no"))
    if getattr(plan.settings, "selected_curves", None) is not None:
        lines.append("{}: {}".format(tr("result_selected_count"), len(plan.settings.selected_curves)))
    lines.append("{}: {} cm".format(tr("result_tolerance"), plan.settings.tolerance_cm))
    lines.append("")
    lines.append("{}: {}".format(tr("result_exact"), len(plan.exact_duplicates_to_delete)))
    lines.append("{}: {}".format(tr("result_line_groups"), len(plan.line_merge_groups)))
    lines.append("{}: {}".format(tr("result_line_delete"), line_count_to_delete(plan)))
    lines.append("{}: {}".format(tr("result_line_create"), line_count_to_create(plan)))
    lines.append("{}: {}".format(tr("result_svg_splines"), plan.svg_straight_spline_candidates))
    lines.append("{}: {}".format(tr("result_svg_skipped"), plan.svg_spline_candidates_skipped))
    lines.append("{}: {}".format(tr("result_circular_groups"), len(plan.circular_merge_groups)))
    lines.append("{}: {}".format(tr("result_circular_delete"), circular_count_to_delete(plan)))
    lines.append("{}: {}".format(tr("result_circular_create"), circular_count_to_create(plan)))
    lines.append("{}: {}".format(tr("result_protected"), plan.protected_skipped))
    lines.append("{}: {}".format(tr("result_constrained"), plan.constrained_groups_skipped))
    lines.append("{}: {}".format(tr("result_total_delete"), total_delete))

    if plan.preview_geometry_limited:
        lines.append("{}: yes".format(tr("result_preview_limited")))

    if plan.selection_limited:
        lines.append("{}: yes".format(tr("result_selection_limited")))

    lines.append("")
    lines.append(tr("partial_limit"))

    if plan.settings.allow_reference_geometry:
        lines.append("")
        lines.append(tr("warning_reference"))

    if plan.settings.allow_constrained_or_dimensioned:
        lines.append("")
        lines.append(tr("warning_constrained"))

    if plan.settings.merge_construction_and_normal:
        lines.append("")
        lines.append(tr("warning_construction"))

    return "\n".join(lines)


def set_textbox_text(textbox, text):
    """
    Set text in a Fusion TextBoxCommandInput safely.
    
        Parameters:
            textbox (adsk.core.TextBoxCommandInput): Text box to update.
            text (str): Plain text to display.
    
        Returns:
            None.
    """
    try:
        textbox.text = text
    except:
        try:
            textbox.formattedText = text.replace("\n", "<br>")
        except:
            pass



# -----------------------------------------------------------------------------
# Version 21 performance helpers: selected-only and line-only fast mode
# -----------------------------------------------------------------------------

def is_supported_selected_curve(entity):
    """Return True when a selected Fusion entity is a supported sketch curve."""
    try:
        ot = entity.objectType
    except:
        return False

    class_names = [
        "SketchLine",
        "SketchArc",
        "SketchCircle",
        "SketchEllipse",
        "SketchEllipticalArc",
        "SketchFittedSpline",
        "SketchControlPointSpline",
    ]

    for name in class_names:
        try:
            if ot == getattr(adsk.fusion, name).classType():
                return True
        except:
            pass

    return False


def selected_curves_from_ui(ui, sketch, settings):
    """Collect selected sketch curves for selected-only analysis."""
    result = []
    seen = set()

    try:
        selections = ui.activeSelections
        count = selections.count
    except:
        return result

    for i in range(count):
        try:
            entity = selections.item(i).entity
        except:
            continue

        if not is_supported_selected_curve(entity):
            continue

        try:
            parent_sketch = entity.parentSketch
            if parent_sketch and parent_sketch != sketch:
                continue
        except:
            pass

        if getattr(settings, "line_only_fast_mode", False):
            if line_like_segment_from_curve(entity, settings) is None:
                continue

        try:
            key = entity.entityToken
        except:
            key = id(entity)

        if key in seen:
            continue

        seen.add(key)
        result.append(entity)

    return result


def is_line_only_fast_curve(curve, settings):
    """Check whether a curve can participate in line-only fast mode."""
    try:
        return line_like_segment_from_curve(curve, settings) is not None
    except:
        return False


def curves_for_exact_duplicate_scan(sketch, settings, plan=None):
    """
    Yield curves for exact duplicate detection using v21 performance rules.

    Selected-only mode never scans the whole sketch. Line-only fast mode scans
    only SketchLine entities, plus near-straight splines when the SVG spline
    option is explicitly enabled.
    """
    selected_curves = getattr(settings, "selected_curves", None)
    if selected_curves is not None:
        for curve in selected_curves:
            if getattr(settings, "line_only_fast_mode", False) and not is_line_only_fast_curve(curve, settings):
                continue
            yield curve
        return

    sc = sketch.sketchCurves

    if getattr(settings, "line_only_fast_mode", False):
        collections = ["sketchLines"]

        if getattr(settings, "treat_near_straight_splines_as_lines", False):
            collections.extend(["sketchFittedSplines", "sketchControlPointSplines"])
        else:
            try:
                if plan:
                    plan.unsupported_skipped += (
                        safe_collection_count(sc, "sketchFittedSplines")
                        + safe_collection_count(sc, "sketchControlPointSplines")
                        + safe_collection_count(sc, "sketchArcs")
                        + safe_collection_count(sc, "sketchCircles")
                        + safe_collection_count(sc, "sketchEllipses")
                        + safe_collection_count(sc, "sketchEllipticalArcs")
                    )
            except:
                pass
    else:
        collections = [
            "sketchLines",
            "sketchArcs",
            "sketchCircles",
            "sketchEllipses",
            "sketchEllipticalArcs",
        ]

        if getattr(settings, "treat_near_straight_splines_as_lines", False):
            collections.extend(["sketchFittedSplines", "sketchControlPointSplines"])
        else:
            try:
                if plan:
                    plan.unsupported_skipped += (
                        safe_collection_count(sc, "sketchFittedSplines")
                        + safe_collection_count(sc, "sketchControlPointSplines")
                    )
            except:
                pass

    for name in collections:
        try:
            col = getattr(sc, name)
            count = col.count

            if name in ("sketchFittedSplines", "sketchControlPointSplines"):
                count = min(count, MAX_SVG_SPLINES_TO_ANALYZE)

            for i in range(count):
                yield col.item(i)
        except:
            pass


def line_like_items_for_plan(plan):
    """Build the line-like curve list used by line merge planning."""
    items = []
    settings = plan.settings
    selected_curves = getattr(settings, "selected_curves", None)

    if selected_curves is not None:
        for curve in selected_curves:
            segment = line_like_segment_from_curve(curve, settings)
            if segment:
                start, end, is_spline = segment
                items.append((curve, start, end, is_spline))
                if is_spline:
                    plan.svg_straight_spline_candidates += 1
        return items

    sc = plan.sketch.sketchCurves

    try:
        lines_col = sc.sketchLines
        for i in range(lines_col.count):
            line = lines_col.item(i)
            segment = line_like_segment_from_curve(line, settings)
            if segment:
                start, end, is_spline = segment
                items.append((line, start, end, is_spline))
    except:
        pass

    if getattr(settings, "treat_near_straight_splines_as_lines", False):
        analyzed_svg_splines = 0
        for collection_name in ("sketchFittedSplines", "sketchControlPointSplines"):
            try:
                col = getattr(sc, collection_name)
                count = col.count

                for i in range(count):
                    if analyzed_svg_splines >= MAX_SVG_SPLINES_TO_ANALYZE:
                        plan.svg_spline_candidates_skipped += max(0, count - i)
                        break

                    spline = col.item(i)
                    analyzed_svg_splines += 1

                    segment = line_like_segment_from_curve(spline, settings)
                    if segment:
                        start, end, is_spline = segment
                        items.append((spline, start, end, is_spline))
                        plan.svg_straight_spline_candidates += 1
            except:
                pass

    return items


def plan_line_merges(plan):
    """Find partially overlapping line-like curves using v21 performance rules."""
    if not plan.settings.merge_partially_overlapping_lines:
        return

    groups = {}

    for line, p1, p2, is_spline in line_like_items_for_plan(plan):
        if not is_deletable_candidate(line, plan.settings, plan):
            continue

        key = line_like_group_key(line, p1, p2, plan.settings)
        if key is None:
            continue

        _construction, ux_q, uy_q, offset_q = key

        ux = ux_q * tol(plan.settings)
        uy = uy_q * tol(plan.settings)
        offset = offset_q * tol(plan.settings)

        length = math.sqrt(ux * ux + uy * uy)
        if length <= tol(plan.settings):
            continue

        ux /= length
        uy /= length

        t1 = projection_on_line(p1, ux, uy)
        t2 = projection_on_line(p2, ux, uy)

        if t2 < t1:
            t1, t2 = t2, t1

        groups.setdefault(key, []).append((t1, t2, line))

    for key, intervals in groups.items():
        if len(intervals) < 2:
            continue

        source_curves = [item[2] for item in intervals]

        if group_has_constraints_or_dimensions(source_curves) and not plan.settings.allow_constrained_or_dimensioned:
            plan.constrained_groups_skipped += 1
            continue

        merged = merge_linear_intervals(intervals, plan.settings)

        if len(merged) >= len(intervals):
            continue

        _construction, ux_q, uy_q, offset_q = key
        ux = ux_q * tol(plan.settings)
        uy = uy_q * tol(plan.settings)
        offset = offset_q * tol(plan.settings)

        length = math.sqrt(ux * ux + uy * uy)
        if length <= tol(plan.settings):
            continue

        ux /= length
        uy /= length

        result_curves = []
        for start_t, end_t, merged_sources in merged:
            start_pt = point_from_line_projection(start_t, offset, ux, uy)
            end_pt = point_from_line_projection(end_t, offset, ux, uy)

            result_curves.append({
                "type": "line",
                "start": start_pt,
                "end": end_pt,
                "isConstruction": resulting_construction_state(merged_sources),
            })

        plan.line_merge_groups.append({
            "source_curves": source_curves,
            "result_curves": result_curves,
        })



def build_cleanup_plan(sketch, settings):
    """Analyze a sketch and build a cleanup plan using v23 mixed SVG rules."""
    plan = CleanupPlan(sketch, settings)

    try:
        counts = sketch_curve_counts(sketch)
        plan.active_guard_curve_count = active_curve_count_for_settings(counts, settings)
        plan.ignored_splines_due_to_svg_disabled = ignored_spline_count_for_settings(counts, settings)
    except:
        pass

    plan_exact_duplicate_removal(plan)
    plan_line_merges(plan)

    if not getattr(settings, "line_only_fast_mode", False):
        plan_circular_merges(plan)

    return plan

# -----------------------------------------------------------------------------
# Command input helpers
# -----------------------------------------------------------------------------

_INPUT_IDS = {
    "intro": "introText",
    "settings_group": "settingsGroup",
    "delete_exact": "deleteExact",
    "selected_only": "selectedOnly",
    "line_only_fast": "lineOnlyFast",
    "merge_lines": "mergeLines",
    "merge_circular": "mergeCircular",
    "svg_splines": "svgSplinesAsLines",
    "allow_large": "allowLargeSketchAnalysis",
    "svg_warning": "svgWarning",
    "allow_reference": "allowReference",
    "allow_constrained": "allowConstrained",
    "merge_construction": "mergeConstruction",
    "tolerance": "toleranceCm",
    "test": "testButton",
    "summary": "summaryText",
}


def add_command_inputs(cmd):
    """
    Create all command dialog inputs.
    
        Parameters:
            cmd (adsk.core.Command): Fusion command being initialized.
    
        Returns:
            None.
    """
    inputs = cmd.commandInputs

    try:
        cmd.okButtonText = tr("apply")
        cmd.cancelButtonText = tr("cancel")
    except:
        pass

    intro_text = "{}\n\n{}: {}".format(
        tr("intro"),
        tr("version_label"),
        ADDIN_VERSION,
    )
    inputs.addTextBoxCommandInput(_INPUT_IDS["intro"], "", intro_text, 4, True)

    group = inputs.addGroupCommandInput(_INPUT_IDS["settings_group"], tr("settings_group"))
    group.isExpanded = True
    group_inputs = group.children

    group_inputs.addBoolValueInput(_INPUT_IDS["delete_exact"], tr("delete_exact"), True, "", True)
    group_inputs.addBoolValueInput(_INPUT_IDS["selected_only"], tr("selected_only"), True, "", False)
    group_inputs.addBoolValueInput(_INPUT_IDS["line_only_fast"], tr("line_only_fast"), True, "", False)
    group_inputs.addBoolValueInput(_INPUT_IDS["merge_lines"], tr("merge_lines"), True, "", True)
    group_inputs.addBoolValueInput(_INPUT_IDS["merge_circular"], tr("merge_circular"), True, "", False)
    group_inputs.addBoolValueInput(_INPUT_IDS["svg_splines"], tr("svg_splines"), True, "", False)
    group_inputs.addBoolValueInput(_INPUT_IDS["allow_large"], tr("allow_large"), True, "", False)
    group_inputs.addTextBoxCommandInput(_INPUT_IDS["svg_warning"], "", tr("svg_warning"), 4, True)

    group_inputs.addBoolValueInput(_INPUT_IDS["allow_reference"], tr("allow_reference"), True, "", False)
    group_inputs.addBoolValueInput(_INPUT_IDS["allow_constrained"], tr("allow_constrained"), True, "", False)
    group_inputs.addBoolValueInput(_INPUT_IDS["merge_construction"], tr("merge_construction"), True, "", False)

    try:
        units_mgr = adsk.core.Application.get().activeProduct.unitsManager
        value_input = adsk.core.ValueInput.createByReal(DEFAULT_TOLERANCE_CM)
        group_inputs.addValueInput(_INPUT_IDS["tolerance"], tr("tolerance"), "cm", value_input)
    except:
        pass

    inputs.addBoolValueInput(_INPUT_IDS["test"], tr("test"), False, "", False)
    inputs.addTextBoxCommandInput(_INPUT_IDS["summary"], tr("summary"), tr("test_hint"), 12, True)


def get_input_by_id(inputs, input_id):
    """
    Find a command input by ID, including inside groups.
    
        Parameters:
            inputs (adsk.core.CommandInputs): Root command input collection.
            input_id (str): ID of the requested input.
    
        Returns:
            adsk.core.CommandInput | None: Matching input or None.
    """
    try:
        item = inputs.itemById(input_id)
        if item:
            return item
    except:
        pass

    # Search group children as a fallback.
    for i in range(inputs.count):
        try:
            item = inputs.item(i)
            if item.id == input_id:
                return item
            if hasattr(item, "children"):
                children = item.children
                for j in range(children.count):
                    child = children.item(j)
                    if child.id == input_id:
                        return child
        except:
            pass

    return None


def read_settings_from_inputs(inputs):
    """
    Read dialog inputs and convert them to CleanupSettings.
    
        Parameters:
            inputs (adsk.core.CommandInputs): Command dialog inputs.
    
        Returns:
            CleanupSettings: Settings object matching the current UI state.
    """
    settings = CleanupSettings()

    def bool_value(input_id, default=False):
        item = get_input_by_id(inputs, input_id)
        if not item:
            return default
        try:
            return bool(item.value)
        except:
            return default

    settings.delete_exact_duplicates = bool_value(_INPUT_IDS["delete_exact"], True)
    settings.selected_geometry_only = bool_value(_INPUT_IDS["selected_only"], False)
    settings.line_only_fast_mode = bool_value(_INPUT_IDS["line_only_fast"], False)
    settings.merge_partially_overlapping_lines = bool_value(_INPUT_IDS["merge_lines"], True)
    settings.merge_partially_overlapping_circular_curves = bool_value(_INPUT_IDS["merge_circular"], False)
    settings.treat_near_straight_splines_as_lines = bool_value(_INPUT_IDS["svg_splines"], False)
    settings.allow_large_sketch_analysis = bool_value(_INPUT_IDS["allow_large"], False)
    settings.allow_reference_geometry = bool_value(_INPUT_IDS["allow_reference"], False)
    settings.allow_constrained_or_dimensioned = bool_value(_INPUT_IDS["allow_constrained"], False)
    settings.merge_construction_and_normal = bool_value(_INPUT_IDS["merge_construction"], False)

    tol_input = get_input_by_id(inputs, _INPUT_IDS["tolerance"])
    if tol_input:
        try:
            settings.tolerance_cm = max(1e-7, float(tol_input.value))
        except:
            settings.tolerance_cm = DEFAULT_TOLERANCE_CM

    return settings


# -----------------------------------------------------------------------------
# Command events
# -----------------------------------------------------------------------------

class CommandState:
    """
    Small state holder for the active command instance.
    
        Attributes:
            last_plan (CleanupPlan | None): Most recent preview/apply plan.
            applied (bool): True when Apply was executed.
    """
    def __init__(self):
        """
        Initialize command runtime state.
        
            Parameters:
                self (CommandState): Instance being initialized.
        
            Returns:
                None.
        """
        self.last_plan = None
        self.applied = False


_command_state = CommandState()


class CommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    """
    Fusion event handler for command input changes.
    
        The handler reacts to the Test button, builds a preview plan, selects curves
        to be removed and creates the temporary preview sketch.
    """
    def notify(self, args):
        """
        Handle Fusion command input change events.
        
            Parameters:
                self (CommandInputChangedHandler): Event handler instance.
                args (adsk.core.InputChangedEventArgs): Fusion event arguments.
        
            Returns:
                None.
        """
        ui = None

        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            changed = args.input
            cmd = args.firingEvent.sender
            inputs = cmd.commandInputs

            if changed.id != _INPUT_IDS["test"]:
                return

            try:
                changed.value = False
            except:
                pass

            sketch = get_target_sketch(app, ui)
            summary_box = get_input_by_id(inputs, _INPUT_IDS["summary"])

            if not sketch:
                if summary_box:
                    set_textbox_text(summary_box, tr("no_sketch"))
                ui.messageBox(tr("no_sketch"), ADDIN_NAME)
                return

            settings = read_settings_from_inputs(inputs)
            delete_preview_sketch(sketch)

            if getattr(settings, "selected_geometry_only", False):
                settings.selected_curves = selected_curves_from_ui(ui, sketch, settings)
                if not settings.selected_curves:
                    _command_state.last_plan = None
                    if summary_box:
                        set_textbox_text(summary_box, tr("selected_none"))
                    return
                guard = None
            else:
                settings.selected_curves = None
                guard = large_sketch_guard_message(sketch, settings)

            if guard:
                _command_state.last_plan = None
                try:
                    ui.activeSelections.clear()
                except:
                    pass
                if summary_box:
                    set_textbox_text(summary_box, guard)
                return

            plan = build_cleanup_plan(sketch, settings)
            _command_state.last_plan = plan

            affected_curves = plan.all_curves_to_delete_or_replace()
            selected = select_curves_for_preview(ui, affected_curves)
            plan.selection_limited = len(affected_curves) > selected

            # Version 22: no temporary preview geometry is created during Test.
            # This avoids expensive sketch-curve creation/recompute on dense SVG imports.
            plan.preview_geometry_limited = False

            if plan.has_changes():
                summary = build_summary(plan, tr("test_completed_no_preview"))
                summary += "\n\n" + tr("no_preview_note")
                summary += "\nSelected curves: {} / {}".format(selected, len(affected_curves))
            else:
                summary = build_summary(plan, tr("nothing_to_preview"))

            if summary_box:
                set_textbox_text(summary_box, summary)

        except:
            if ui:
                ui.messageBox("Preview error:\n\n{}".format(traceback.format_exc()), ADDIN_NAME)


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    """
    Fusion event handler for the Apply action.
    
        This handler rebuilds the cleanup plan from current inputs and applies it
        permanently to the target sketch.
    """
    def notify(self, args):
        """
        Handle Fusion command execution.
        
            Parameters:
                self (CommandExecuteHandler): Event handler instance.
                args (adsk.core.CommandEventArgs): Fusion event arguments.
        
            Returns:
                None.
        """
        ui = None

        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            cmd = args.firingEvent.sender
            inputs = cmd.commandInputs

            sketch = get_target_sketch(app, ui)
            if not sketch:
                ui.messageBox(tr("no_sketch"), ADDIN_NAME)
                return

            settings = read_settings_from_inputs(inputs)
            delete_preview_sketch(sketch)

            if getattr(settings, "selected_geometry_only", False):
                settings.selected_curves = selected_curves_from_ui(ui, sketch, settings)
                if not settings.selected_curves:
                    ui.messageBox(tr("selected_none"), ADDIN_NAME)
                    return
                guard = None
            else:
                settings.selected_curves = None
                guard = large_sketch_guard_message(sketch, settings)

            if guard:
                ui.messageBox(guard, ADDIN_NAME)
                return

            plan = build_cleanup_plan(sketch, settings)

            deleted, created = apply_cleanup_plan(plan)

            _command_state.last_plan = plan
            _command_state.applied = True

            summary = build_summary(plan, tr("cleanup_completed"))
            summary += "\n\nDeleted/replaced curves: {}".format(deleted)
            summary += "\nCreated replacement curves: {}".format(created)

            ui.messageBox(summary, ADDIN_NAME)

        except:
            if ui:
                ui.messageBox("Apply error:\n\n{}".format(traceback.format_exc()), ADDIN_NAME)


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    """
    Fusion event handler called when the command closes.
    
        It removes the temporary preview sketch and clears selection when the user
        exits the command.
    """
    def notify(self, args):
        """
        Handle command destruction/closing.
        
            Parameters:
                self (CommandDestroyHandler): Event handler instance.
                args (adsk.core.CommandEventArgs): Fusion event arguments.
        
            Returns:
                None.
        """
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            sketch = get_target_sketch(app, ui)

            if sketch:
                delete_preview_sketch(sketch)

            try:
                ui.activeSelections.clear()
            except:
                pass

            _command_state.last_plan = None
            _command_state.applied = False

        except:
            pass


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    """
    Fusion event handler called when the command is created.
    
        It adds dialog inputs and registers the input, execute and destroy handlers.
    """
    def notify(self, args):
        """
        Initialize the command when Fusion creates it.
        
            Parameters:
                self (CommandCreatedHandler): Event handler instance.
                args (adsk.core.CommandCreatedEventArgs): Fusion event arguments.
        
            Returns:
                None.
        """
        ui = None

        try:
            app = adsk.core.Application.get()
            ui = app.userInterface

            cmd = adsk.core.Command.cast(args.command)
            add_command_inputs(cmd)

            input_changed = CommandInputChangedHandler()
            execute = CommandExecuteHandler()
            destroy = CommandDestroyHandler()

            cmd.inputChanged.add(input_changed)
            cmd.execute.add(execute)
            cmd.destroy.add(destroy)

            _handlers.extend([input_changed, execute, destroy])

        except:
            if ui:
                ui.messageBox("Command creation error:\n\n{}".format(traceback.format_exc()), ADDIN_NAME)


# -----------------------------------------------------------------------------
# UI installation
# -----------------------------------------------------------------------------

def get_panel_by_id(ui, panel_id):
    """
    Find a Fusion toolbar panel by internal ID.
    
        Parameters:
            ui (adsk.core.UserInterface): Fusion UI object.
            panel_id (str): Internal panel ID to search for.
    
        Returns:
            adsk.core.ToolbarPanel | None: Matching panel or None.
    """
    try:
        panel = ui.allToolbarPanels.itemById(panel_id)
        if panel:
            return panel
    except:
        pass

    for workspace_id in WORKSPACE_CANDIDATES:
        try:
            workspace = ui.workspaces.itemById(workspace_id)
            if not workspace:
                continue
            panel = workspace.toolbarPanels.itemById(panel_id)
            if panel:
                return panel
        except:
            pass

    return None


def add_command_to_panel(ui, cmd_def, panel_id):
    """
    Add the cleaner command button to a toolbar panel.
    
        Parameters:
            ui (adsk.core.UserInterface): Fusion UI object.
            cmd_def (adsk.core.CommandDefinition): Command definition to add.
            panel_id (str): Internal target panel ID.
    
        Returns:
            adsk.core.ToolbarControl | None: Created or existing control.
    """
    panel = get_panel_by_id(ui, panel_id)
    if not panel:
        return None

    try:
        existing = panel.controls.itemById(CMD_ID)
        if existing:
            return existing
    except:
        pass

    try:
        control = panel.controls.addCommand(cmd_def)
        try:
            control.isPromoted = True
            control.isPromotedByDefault = True
        except:
            pass
        _added_controls.append(control)
        return control
    except:
        return None


def install_ui(ui):
    """
    Install the add-in command definition and toolbar button.
    
        Parameters:
            ui (adsk.core.UserInterface): Fusion UI object.
    
        Returns:
            None.
    """
    global _added_command_definition

    cmd_defs = ui.commandDefinitions
    cmd_def = cmd_defs.itemById(CMD_ID)

    if cmd_def:
        try:
            cmd_def.deleteMe()
        except:
            pass

    cmd_def = cmd_defs.addButtonDefinition(
        CMD_ID,
        "{} {}".format(tr(CMD_NAME_KEY), ADDIN_VERSION),
        "{}\n{}: {}".format(tr(CMD_DESCRIPTION_KEY), tr("version_label"), ADDIN_VERSION),
        "",
    )

    _added_command_definition = cmd_def

    created_handler = CommandCreatedHandler()
    cmd_def.commandCreated.add(created_handler)
    _handlers.append(created_handler)

    added_anywhere = False

    for panel_id in PANEL_CANDIDATES:
        control = add_command_to_panel(ui, cmd_def, panel_id)
        if control:
            added_anywhere = True

    if not added_anywhere:
        for panel_id in FALLBACK_PANEL_CANDIDATES:
            control = add_command_to_panel(ui, cmd_def, panel_id)
            if control:
                added_anywhere = True
                break

    if not added_anywhere:
        ui.messageBox(tr("addin_loaded_no_panel"), ADDIN_NAME)


def uninstall_ui(ui):
    """
    Remove toolbar controls and command definitions installed by the add-in.
    
        Parameters:
            ui (adsk.core.UserInterface): Fusion UI object.
    
        Returns:
            None.
    """
    global _added_command_definition

    for control in list(_added_controls):
        try:
            if control and control.isValid:
                control.deleteMe()
        except:
            pass

    _added_controls.clear()

    try:
        cmd_def = ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            cmd_def.deleteMe()
    except:
        pass

    _added_command_definition = None


# -----------------------------------------------------------------------------
# Add-in entry points
# -----------------------------------------------------------------------------

def run(context):
    """
    Fusion 360 add-in entry point.
    
        Parameters:
            context: Fusion startup context provided by the host application.
    
        Returns:
            None.
    """
    ui = None

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        install_ui(ui)

    except:
        if ui:
            ui.messageBox("Add-in start error:\n\n{}".format(traceback.format_exc()), ADDIN_NAME)


def stop(context):
    """
    Fusion 360 add-in shutdown entry point.
    
        Parameters:
            context: Fusion shutdown context provided by the host application.
    
        Returns:
            None.
    """
    ui = None

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        uninstall_ui(ui)

    except:
        if ui:
            ui.messageBox("Add-in stop error:\n\n{}".format(traceback.format_exc()), ADDIN_NAME)
