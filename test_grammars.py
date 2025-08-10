# No special path manipulation is needed because this script is in the project root.
# Python automatically adds the script's directory to the path.

from building_grammar.core import parse, GrammarError
from building_grammar.pattern_resolver import PatternResolver, ResolutionError
from building_grammar.design_spec import BuildingSpec, FacadeSpec, BuildingDirector


from building_grammar.building_generator import BuildingGenerator
from gui.resources_loader import IconFiles # Import from its location

from building_grammar.building_generator import BuildingGenerator # <-- NEW IMPORT

def run_test(test_function):
    """A simple decorator to run a test and print its status."""

    def wrapper():
        test_name = test_function.__name__
        print(f"--- Running: {test_name} ---")
        try:
            test_function()
            print(f"✅ PASS: {test_name}\n")
            return True
        except AssertionError as e:
            print(f"❌ FAIL: {test_name}")
            print(f"   Assertion failed: {e}\n")
            return False
        except Exception as e:
            print(f"💥 ERROR: {test_name}")
            print(f"   An unexpected error occurred: {type(e).__name__}: {e}\n")
            return False

    return wrapper


# # --- Test Cases ---
#
# def test_simple_grammar_parsing():
#     """Tests if the core parser can handle a basic valid string."""
#     grammar = "[A]<B-C>"
#     pattern = parse(grammar)
#     assert len(pattern.floors) == 1, "Should have 1 floor"
#     assert len(pattern.floors[0]) == 2, "Floor should have 2 groups"
#     assert pattern.to_string() == "[A]-<B-C>", "Canonical string representation should match"
#
#
# def test_multi_floor_parsing():
#     """Tests parsing of a multi-line grammar string."""
#     grammar = "<A>\n[B]2"
#     pattern = parse(grammar)
#     assert len(pattern.floors) == 2, "Should have 2 floors"
#     assert pattern.floors[0][0].to_string() == "<A>", "First floor should be <A>"
#     assert pattern.floors[1][0].to_string() == "[B]2", "Second floor should be [B]2"
#
#
# def test_invalid_grammar_raises_error():
#     """Ensures the parser rejects malformed strings."""
#     invalid_grammar = "[A]]<B>"
#     try:
#         parse(invalid_grammar)
#         # If this line is reached, the test fails because no error was raised.
#         assert False, "GrammarError was not raised for invalid syntax"
#     except GrammarError:
#         # This is the expected outcome.
#         assert True
#     except Exception:
#         assert False, "An unexpected exception type was raised"
#
#
# def test_simple_pattern_resolution():
#     """Tests the resolver with a basic case and default module widths."""
#     resolver = PatternResolver(default_module_width=100)
#     grammar = "[D]<W>"
#     # Target width 500: 100 for [D], 400 for <W>. <W> should contain 4 'W's.
#     resolved = resolver.resolve(grammar, floor_widths={0: 500})
#
#     expected_floor = ['D', 'W', 'W', 'W', 'W']
#     assert resolved[0] == expected_floor, f"Resolved pattern mismatch. Got {resolved[0]}"
#
#
# def test_resolution_with_multiple_fill_groups():
#     """Tests if the resolver correctly divides space between multiple fill groups."""
#     resolver = PatternResolver(default_module_width=50)
#     grammar = "<A>[B]<C>"
#     # Target 500: 50 for [B], leaving 450. 225 for <A> and 225 for <C>.
#     # Each fill group should contain 4 modules (4 * 50 = 200).
#     resolved = resolver.resolve(grammar, floor_widths={0: 500})
#
#     expected_floor = ['A', 'A', 'A', 'A', 'B', 'C', 'C', 'C', 'C']
#     assert resolved[0] == expected_floor, f"Resolved pattern mismatch. Got {resolved[0]}"
#
#
# def test_resolution_error_on_impossible_width():
#     """Ensures the resolver fails when rigid parts are too wide."""
#     resolver = PatternResolver(default_module_width=100)
#     grammar = "[A][B][C]"
#     try:
#         resolver.resolve(grammar, floor_widths={0: 200})  # 300px required, 200px given
#         assert False, "ResolutionError was not raised"
#     except ResolutionError:
#         assert True
#
#
# def test_design_spec_creation():
#     """Tests that the BuildingSpec dataclass can be instantiated correctly."""
#     spec = BuildingSpec(
#         facades={
#             "front": FacadeSpec(grammar="<W>", width=500),
#             "right": FacadeSpec(grammar="[D]", width=100),
#         }
#     )
#     assert spec.facades["front"].width == 500
#     assert spec.camera_angle == 30  # Check default value
#
#
#
# def test_verbose_multi_floor_facade_resolution():
#     """
#     A verbose test to demonstrate how the resolver handles a complex
#     5-floor pattern with mixed rigid and fill groups.
#     """
#     print("   Setting up test...")
#     # --- Test Setup ---
#     resolver = PatternResolver(default_module_width=100)
#
#     # This is the complex grammar string for a single 5-floor facade
#     grammar = """
#     <Wall00>
#     [Wall00]<Window00>
#     [Wall00]<Window00>
#     [Wall00]<Window00>
#     [Wall00]<Window00-Wall00>[Door00]<Window00>[Wall00]
#     """
#
#     # We'll assign a different width to the ground floor to test flexibility
#     floor_widths = {
#         0: 800,  # Top floor
#         1: 800,
#         2: 800,
#         3: 800,
#         4: 800  # Ground floor target width
#     }
#
#     print(f"   Grammar defined for {len(floor_widths)} floors.")
#     print(f"   Default module width set to: {resolver.default_module_width}px")
#     print("   Target widths per floor:", floor_widths)
#     print("\n   Starting resolution process...")
#
#     # --- Execution ---
#     resolved_facade = resolver.resolve(grammar, floor_widths)
#
#     print("   Resolution complete. Now validating results...\n")
#
#     # --- Validation: Floor 0 (Top Floor) ---
#     # This part was correct and remains unchanged.
#     floor_idx = 0
#     print(f"   --- Validating Floor {floor_idx} (Target: {floor_widths[floor_idx]}px) ---")
#     print(f"   Grammar: '<Wall00>'")
#     actual_floor = resolved_facade[floor_idx]
#     actual_width = len(actual_floor) * resolver.default_module_width
#     print(f"   Logic: No rigid parts. One fill group gets all {floor_widths[floor_idx]}px of space.")
#     print(f"   Expected module count: {floor_widths[floor_idx]} // {resolver.default_module_width} = {800 // 100}")
#     print(f"   Actual resolved modules ({len(actual_floor)}): {actual_floor}")
#     print(f"   Actual width: {actual_width}px")
#     assert len(actual_floor) == 8, f"Floor {floor_idx} should have 8 modules"
#
#     # --- Validation: Floors 1, 2, 3 ---
#     # This part was also correct and remains unchanged.
#     for floor_idx in [1, 2, 3]:
#         print(f"\n   --- Validating Floor {floor_idx} (Target: {floor_widths[floor_idx]}px) ---")
#         print(f"   Grammar: '[Wall00]<Window00>'")
#         actual_floor = resolved_facade[floor_idx]
#         actual_width = len(actual_floor) * resolver.default_module_width
#         rigid_width = 100
#         fill_width = floor_widths[floor_idx] - rigid_width
#         print(f"   Logic: Rigid part [Wall00] takes {rigid_width}px. Remaining {fill_width}px for the fill group.")
#         print(f"   Expected fill module count: {fill_width} // {resolver.default_module_width} = {700 // 100}")
#         print(f"   Actual resolved modules ({len(actual_floor)}): {actual_floor}")
#         print(f"   Actual width: {actual_width}px")
#         expected_modules = ['Wall00'] + ['Window00'] * 7
#         assert actual_floor == expected_modules, f"Floor {floor_idx} resolved incorrectly"
#
#     # =========================================================================
#     # --- THIS IS THE CORRECTED SECTION ---
#     # =========================================================================
#     floor_idx = 4
#     target_width_floor4 = floor_widths[floor_idx]  # 800px
#
#     print(f"\n   --- Validating Floor {floor_idx} (Target: {target_width_floor4}px) ---")
#     # Corrected the grammar string to match the input
#     print(f"   Grammar: '[Wall00]<Window00-Wall00>[Door00]<Window00>[Wall00]'")
#
#     actual_floor = resolved_facade[floor_idx]
#     actual_width = sum(resolver._get_module_width(m) for m in actual_floor)
#
#     # Calculation remains the same
#     rigid_width = 300  # [Wall00] + [Door00] + [Wall00]
#     fill_width = target_width_floor4 - rigid_width  # 800 - 300 = 500
#     fill_width_per_group = fill_width // 2  # 500 // 2 = 250
#
#     print(f"   Logic: 3 rigid parts take {rigid_width}px. Remaining {fill_width}px for 2 fill groups.")
#     print(f"   Space per fill group: {fill_width_per_group}px")
#
#     # Corrected logic description
#     print(f"   Fill Group 1 (<Window00-Wall00>): Should fit 'Window00', 'Wall00' (100+100=200px)")
#     print(f"   Fill Group 2 (<Window00>): Should fit 'Window00', 'Window00' (100+100=200px)")
#
#     print(f"   Actual resolved modules ({len(actual_floor)}): {actual_floor}")
#     print(f"   Actual width: {actual_width}px")
#
#     # Corrected the expected module list to match the logic
#     expected_modules = (
#             ['Wall00']  # Rigid
#             + ['Window00', 'Wall00']  # Fill 1
#             + ['Door00']  # Rigid
#             + ['Window00', 'Window00']  # Fill 2
#             + ['Wall00']  # Rigid
#     )
#     assert actual_floor == expected_modules, "Floor 4 resolved incorrectly"
#
#
# def test_end_to_end_resolution_with_dataclass():
#     """
#     Tests the full resolution process using the BuildingSpec dataclass
#     and prints the final resolved structure.
#     """
#     # --- 1. Define the Building Design using our Dataclasses ---
#     # This is the "input" to our entire system.
#     building_design = BuildingSpec(
#         default_module_width=100,
#         facades={
#             "front": FacadeSpec(
#                 width=1200,
#                 grammar="""<Wall00>
# [Wall00]<Window00>
# [Wall00]<Window00-Wall00>[Door00]<Window00>[Wall00]"""
#             ),
#             "right": FacadeSpec(
#                 width=500,
#                 grammar="<Window00>\n[Wall00]\n[Wall00-Door00]"
#             )
#         }
#     )
#
#     # --- 2. Instantiate the Resolver ---
#     resolver = PatternResolver(
#         default_module_width=building_design.default_module_width
#     )
#
#     # This dictionary will hold the final, resolved output
#     resolved_building = {}
#
#     print("   --- Input Building Specification ---")
#     print(f"   Default Module Width: {building_design.default_module_width}px")
#
#     # --- 3. Process Each Facade Defined in the Spec ---
#     for side, facade_spec in building_design.facades.items():
#         print(f"\n   Resolving Facade: '{side}' (Target Width: {facade_spec.width}px)")
#
#         # The resolver needs a floor_widths dict. We create it from the spec.
#         num_floors = len([line for line in facade_spec.grammar.strip().splitlines() if line.strip()])
#         floor_widths = {i: facade_spec.width for i in range(num_floors)}
#
#         # This is the core action: resolving the grammar for one facade
#         resolved_facade = resolver.resolve(facade_spec.grammar, floor_widths)
#         resolved_building[side] = resolved_facade
#
#     # --- 4. Print the Final, Clean Output ---
#     print("\n\n   ============================================")
#     print("   ✅ Final Resolved Building Structure")
#     print("   ============================================")
#     for side, floors in resolved_building.items():
#         print(f"\n   FACADE: {side}")
#         print("   ----------------------------------------")
#         for floor_idx, modules in floors.items():
#             # Use f-string formatting to align the output neatly
#             print(f"     Floor {floor_idx}: {modules}")
#     print("   ============================================\n")
#
#     # --- 5. Add a simple assertion to make it a real test ---
#     # Let's just check if the 'front' facade was resolved.
#     assert "front" in resolved_building, "Front facade was not resolved."
#     # And check the number of floors on the 'right' facade.
#     assert len(resolved_building["right"]) == 3, "Right facade should have 3 floors."
#
# # --- Main Execution Block ---
#
# def test_director_with_default_facades():
#     """
#     Tests that the BuildingDirector correctly creates default facades
#     for missing sides (back and left).
#     """
#     # --- 1. Define an INCOMPLETE Building Design ---
#     # We define num_floors once, as the source of truth.
#     incomplete_spec = BuildingSpec(
#         num_floors=2,  # Define building height here
#         default_module_width=100,
#         facades={
#             "front": FacadeSpec(
#                 width=500,
#                 grammar="<D>\n[W]"  # Grammar must have 2 floors
#             ),
#             "right": FacadeSpec(
#                 width=300,
#                 grammar="<Win>\n<Win>"  # Grammar must have 2 floors
#             ),
#         }
#     )
#
#     # --- 2. Use the Director to process the spec ---
#     print("\n   --- Initializing Director with Incomplete Spec ---")
#     director = BuildingDirector(spec=incomplete_spec)
#
#     # --- 3. Produce the final blueprint ---
#     blueprint = director.produce_blueprint()
#
#     # --- 4. Print and Validate ---
#     print("\n   --- Final Blueprint Produced by Director ---")
#     for side, floors in blueprint.items():
#         print(f"\n   FACADE: {side}")
#         for floor_idx, modules in floors.items():
#             print(f"     Floor {floor_idx}: {modules}")
#
#     # Assertions to confirm the default logic worked
#     assert "back" in blueprint, "Director should have created a 'back' facade."
#     assert "left" in blueprint, "Director should have created a 'left' facade."
#
#     # Check if the back facade matches the front's properties
#     assert len(blueprint["back"]) == 2, "Default 'back' facade has wrong number of floors."
#     assert blueprint["back"][0] == ['Wall00'] * 5, "Default 'back' floor 0 is incorrect."
#
#     # Check if the left facade matches the right's properties
#     assert len(blueprint["left"]) == 2, "Default 'left' facade has wrong number of floors."
#     assert blueprint["left"][0] == ['Wall00'] * 3, "Default 'left' floor 0 is incorrect."
#
#
# def test_director_autofills_and_validates_floors():
#     """
#     Tests that the Director autofills facades with too few floors and
#     raises an error for facades with too many floors.
#     """
#     # --- Test Case 1: Autofill a facade with missing floors ---
#     print("\n   --- Testing autofill for a 1-floor grammar in a 3-floor building ---")
#     spec_with_missing_floors = BuildingSpec(
#         num_floors=3,
#         facades={
#             "front": FacadeSpec(width=500, grammar="<D>"), # Only 1 floor provided
#             "right": FacadeSpec(width=300, grammar="<W>\n<W>\n<W>"),
#         }
#     )
#     director = BuildingDirector(spec=spec_with_missing_floors)
#     # Check if the director's internal spec was corrected
#     front_facade_after_norm = director.completed_spec.facades["front"]
#     expected_grammar = "<D>\n<Wall00>\n<Wall00>"
#     assert front_facade_after_norm.grammar == expected_grammar
#     print("   ✅ Autofill test passed.")
#
#     # --- Test Case 2: Raise error for a facade with too many floors ---
#     print("\n   --- Testing error for a 4-floor grammar in a 3-floor building ---")
#     spec_with_too_many_floors = BuildingSpec(
#         num_floors=3,
#         facades={
#             "front": FacadeSpec(width=500, grammar="<D>\n<D>\n<D>\n<D>"),
#             "right": FacadeSpec(width=300, grammar="<W>\n<W>\n<W>"),
#         }
#     )
#     try:
#         BuildingDirector(spec=spec_with_too_many_floors)
#         # If this line is reached, the test fails
#         assert False, "ValueError was not raised for facade with too many floors"
#     except ValueError as e:
#         print(f"   ✅ Correctly caught expected error: {e}")
#         assert "has 4 floors" in str(e) # Check that the error message is correct
#
#
# def test_director_print_representation():
#     """
#     Tests the __str__ method of the BuildingDirector for a clear output.
#     """
#     spec = BuildingSpec(
#         num_floors=2,
#         default_module_width=100,
#         facades={
#             "front": FacadeSpec(width=500, grammar="<D>\n[W]"),
#             "right": FacadeSpec(width=300, grammar="<Win>\n<Win>"),
#         }
#     )
#
#     print("\n   --- Initializing Director and generating blueprint ---")
#     director = BuildingDirector(spec=spec)
#
#     # Now, just print the director object directly!
#     # The __str__ method will be called automatically.
#     print(director)
#
#     # We can add a simple assertion to make sure it's a real test
#     blueprint = director.produce_blueprint()
#     assert "back" in blueprint and "left" in blueprint
#

@run_test
def test_generator_with_resources_loader():
    """
    Tests that the BuildingGenerator can be fed by the IconFiles catalogue.
    """
    print("\n   --- Testing Integration: IconFiles -> BuildingGenerator ---")

    # --- 1. Use IconFiles to find the modules ---
    # This assumes you have a "Default" sub-directory in your "resources" folder
    category_to_use = "Default"
    print(f"   Loading icon set for category: '{category_to_use}'")

    # We might need to reload if files have changed, or rely on the initial scan
    IconFiles.reload()
    icon_set = IconFiles.get_icons_for_category(category_to_use)

    if not icon_set:
        assert False, f"No icons found for category '{category_to_use}' in IconFiles."

    # --- 2. Pass the discovered icon set to the Generator ---
    try:
        generator = BuildingGenerator(icon_set=icon_set)

        # --- 3. Test the generator as before ---
        floor_blueprint = ['Wall00', 'Door00', 'Window00']
        # Check if all needed modules were loaded
        for module in floor_blueprint:
            if module not in generator.modules:
                assert False, f"Module '{module}' from blueprint not found in loaded generator modules."

        flat_floor_image = generator.assemble_flat_floor(floor_blueprint)
        output_filename = "test_output_integrated.png"
        flat_floor_image.save(output_filename)

        print(f"   Successfully generated '{output_filename}' using integrated loaders.")
        assert flat_floor_image.width > 0

    except Exception as e:
        print(f"   ERROR during integrated test: {e}")
        assert False, "Test failed due to an exception."


@run_test
def test_facade_generation_workflow():
    """
    Tests the primary workflow: Spec -> Director -> Blueprint -> Generator -> Image.
    This test is simplified to show the core process.
    """
    # -------------------------------------------------------------------
    # STEP 1: DEFINE the building design with a simple specification.
    # -------------------------------------------------------------------
    # We want a 2-floor building. The front should be about 500px wide.
    building_spec = BuildingSpec(
        num_floors=2,
        facades={
            "front": FacadeSpec(width=2250, grammar="[Window01]<Wall00>[Window01]\n[Door00]<Wall00-Window00>"),
            "right": FacadeSpec(width=384, grammar="<Window00>\n<Window00>[Window01]"),
        }
    )

    # -------------------------------------------------------------------
    # STEP 2: DIRECT the construction to get a complete blueprint.
    # -------------------------------------------------------------------
    # The director handles all the complex logic (defaults, normalization).
    director = BuildingDirector(spec=building_spec)
    blueprint = director.produce_blueprint()

    # -------------------------------------------------------------------
    # STEP 3: GENERATE the facade image from the blueprint.
    # -------------------------------------------------------------------
    # The generator handles the visual part (loading and pasting images).
    icon_set = IconFiles.get_icons_for_category("Default")
    generator = BuildingGenerator(icon_set=icon_set)

    # We only want to generate the image for the "front" facade.
    front_facade_image = generator.assemble_full_facade(blueprint["front"])

    # -------------------------------------------------------------------
    # STEP 4: VERIFY the output and save it.
    # -------------------------------------------------------------------
    output_filename = "test_output_facade.png"
    print(f"   Workflow complete. Saving final facade image to '{output_filename}'")
    front_facade_image.save(output_filename)

    # Simple, meaningful assertions.
    # The image should exist and have a real size.
    assert front_facade_image.width > 0

    # The height should match our design specification.
    expected_height = building_spec.num_floors * 128
    assert front_facade_image.height == expected_height, \
        f"Image height is {front_facade_image.height}, but expected {expected_height}"

    print(f"   Image dimensions: {front_facade_image.size}. Verification passed.")


if __name__ == "__main__":
    print("====================================")
    print("       Running Grammar Tests        ")
    print("====================================\n")

    # List all the test functions you want to run
    tests_to_run = [

        test_generator_with_resources_loader,
        test_facade_generation_workflow
    ]

    results = [test() for test in tests_to_run]

    print("\n------------------------------------")
    print("            Test Summary            ")
    print("------------------------------------")
    passed_count = sum(1 for r in results if r)
    failed_count = len(results) - passed_count
    print(f"  Passed: {passed_count}")
    print(f"  Failed: {failed_count}")
    print("====================================\n")

    # Exit with a non-zero code if any tests failed, useful for automation
    if failed_count > 0:
        exit(1)