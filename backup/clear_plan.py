"""What gets cleared at the start of a new month: the senarai semak only.
Kept: buildings, doors, resident names, the map, every defect that is NOT yet Selesai, and all permanent defect records (defectLog)."""
from report_builder import is_open


def indexed(v):
    """(key, value) pairs of a Firebase array (list or {index: value})."""
    if isinstance(v, list): return [(i, x) for i, x in enumerate(v) if x]
    if isinstance(v, dict): return [(k, x) for k, x in v.items() if x]
    return []


def plan_clear(layouts):
    """Return {firebase path: None} for a multi-path PATCH on the database root."""
    out = {}
    for lid, layout in (layouts or {}).items():
        for el in ((layout or {}).get('elements') or {}).values():
            base = f'layouts/{lid}/elements/{el.get("id")}'
            if el.get('category') == 'pekerja':
                for i, door in indexed(el.get('doors')):
                    if door.get('checklist'):
                        out[f'{base}/doors/{i}/checklist'] = None
                    for key, e in (door.get('defects') or {}).items():
                        if not is_open(e): out[f'{base}/doors/{i}/defects/{key}'] = None
            else:
                for key, e in (el.get('defects') or {}).items():
                    if not is_open(e): out[f'{base}/defects/{key}'] = None
    return out
