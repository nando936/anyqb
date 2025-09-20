"""Search all preferences for cash/accrual setting"""

import sys
sys.path.insert(0, 'src')

from qb.shared_utilities.fast_qb_connection import FastQBConnection

def test_all_preferences():
    """Check ALL preference sections"""
    conn = FastQBConnection()

    if not conn.connect():
        print("[ERROR] Failed to connect to QuickBooks")
        return

    try:
        # Query preferences
        request_set = conn.create_request_set()
        prefs_query = request_set.AppendPreferencesQueryRq()

        print("Querying ALL company preferences...")
        print("="*60)

        response_set = conn.process_request_set(request_set)
        response = response_set.ResponseList.GetAt(0)

        if response.StatusCode == 0:
            print("[SUCCESS] Got preferences\n")

            if response.Detail:
                prefs = response.Detail

                # List ALL preference sections
                all_attrs = [a for a in dir(prefs) if not a.startswith('_')]
                pref_sections = []

                for attr in all_attrs:
                    if 'Preferences' in attr and not attr.startswith(('Get', 'Set')):
                        pref_sections.append(attr)

                print(f"Found {len(pref_sections)} preference sections:")
                for section in pref_sections:
                    print(f"  - {section}")

                print("\n" + "="*60)
                print("Checking each section for report/cash/accrual settings:")
                print("="*60)

                # Check each preference section
                for section_name in pref_sections:
                    section = getattr(prefs, section_name, None)
                    if section:
                        print(f"\n{section_name}:")

                        # Get all attributes of this section
                        section_attrs = [a for a in dir(section) if not a.startswith('_')]

                        # Look for relevant attributes
                        found_relevant = False
                        for attr in section_attrs:
                            if any(keyword in attr.lower() for keyword in ['report', 'basis', 'cash', 'accrual', 'summary']):
                                try:
                                    val = getattr(section, attr)
                                    if hasattr(val, 'GetValue'):
                                        value = val.GetValue()
                                        print(f"  {attr}: {value}")
                                        found_relevant = True

                                        # If it's a basis setting, decode it
                                        if 'basis' in attr.lower():
                                            if value == 0:
                                                print(f"    (0 = Accrual)")
                                            elif value == 1:
                                                print(f"    (1 = Cash)")
                                            elif value == 2:
                                                print(f"    (2 = None)")
                                except:
                                    pass

                        if not found_relevant:
                            # List all attributes for this section
                            print("  No report/basis settings found. All attributes:")
                            for attr in section_attrs:
                                if not attr.startswith(('Get', 'Set', 'Release', 'Query', 'Invoke', 'Type')):
                                    try:
                                        val = getattr(section, attr)
                                        if hasattr(val, 'GetValue'):
                                            print(f"    {attr}: {val.GetValue()}")
                                    except:
                                        pass

                # Also check if there's a global reporting basis
                print("\n" + "="*60)
                print("Checking for global settings:")
                print("="*60)

                # Check main preference object attributes
                for attr in all_attrs:
                    if any(keyword in attr.lower() for keyword in ['report', 'basis', 'cash', 'accrual']):
                        if not attr.startswith(('Get', 'Set')) and 'Preferences' not in attr:
                            try:
                                val = getattr(prefs, attr)
                                if hasattr(val, 'GetValue'):
                                    print(f"  {attr}: {val.GetValue()}")
                            except:
                                pass
        else:
            print(f"[ERROR] {response.StatusMessage}")

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    test_all_preferences()