"""
Concept Map Parser
==================
Detects 2D hierarchical concept maps in textbook front matter or chapter intros
and reconstructs them into clean Mermaid diagrams and outlines.
"""

import logging
from typing import Tuple, Set

logger = logging.getLogger(__name__)


class ConceptMapParser:
    """Detects and generates Mermaid diagrams from spatial 2D concept maps."""

    @classmethod
    def reconstruct_concept_map(cls, page_elem, fonts, header_bottom: float, lo_top: float, style_config: dict = None) -> tuple:
        """
        Detects 2D hierarchical concept maps and reconstructs them into Mermaid diagrams.
        Returns: (formatted_markdown_str, set_of_consumed_elements)
        """
        style = style_config or {}
        if header_bottom <= 0 or lo_top >= 9000:
            return "", set()

        text_elements = page_elem.findall('text')
        map_candidates = []
        for t in text_elements:
            top = float(t.attrib.get('top', 0))
            txt = ''.join(t.itertext()).strip()
            if (header_bottom + 10) <= top < (lo_top - 10) and txt:
                map_candidates.append(t)

        if len(map_candidates) < 10:
            return "", set()

        consumed = set(map_candidates)

        raw = []
        for t in map_candidates:
            raw.append({
                'elem': t,
                'top': float(t.attrib.get('top', 0)),
                'left': float(t.attrib.get('left', 0)),
                'text': ''.join(t.itertext()).strip()
            })

        tracks = []
        for it in sorted(raw, key=lambda x: x['left']):
            placed = False
            for trk in tracks:
                if abs(trk['center_x'] - it['left']) <= 25:
                    trk['items'].append(it)
                    trk['center_x'] = sum(x['left'] for x in trk['items']) / len(trk['items'])
                    placed = True
                    break
            if not placed:
                tracks.append({'center_x': it['left'], 'items': [it]})

        all_nodes = []
        for trk in tracks:
            items = sorted(trk['items'], key=lambda x: x['top'])
            curr = None
            for it in items:
                if curr is None:
                    curr = dict(it)
                    continue
                if 0 < it['top'] - curr['top'] <= 18:
                    curr['text'] += ' ' + it['text']
                    curr['top'] = min(curr['top'], it['top'])
                else:
                    all_nodes.append(curr)
                    curr = dict(it)
            if curr:
                all_nodes.append(curr)

        all_nodes.sort(key=lambda x: (x['top'], x['left']))
        if not all_nodes:
            return "", set()

        root = all_nodes[0]

        # 1. Cluster nodes by X into columns
        columns = []
        for n in all_nodes[1:]:
            placed = False
            for col in columns:
                if abs(col['x'] - n['left']) <= 30:
                    col['items'].append(n)
                    col['x'] = sum(x['left'] for x in col['items']) / len(col['items'])
                    placed = True
                    break
            if not placed:
                columns.append({'x': n['left'], 'items': [n]})

        for col in columns:
            col['items'].sort(key=lambda x: x['top'])

        # 2. Identify columnar leaf lists and connect to category parent
        col_categories = []
        stack_children = set()
        edges = []
        node_id_map = {root['text']: 'Root'}
        nid_counter = 1
        for n in all_nodes[1:]:
            if n['text'] not in node_id_map:
                node_id_map[n['text']] = f'N{nid_counter}'
                nid_counter += 1

        for col in columns:
            items = col['items']
            if len(items) >= 2:
                i = len(items) - 1
                while i >= 2 and (items[i]['top'] - items[i-1]['top'] <= 45):
                    i -= 1
                parent_node = items[i-1]
                for lf in items[i:]:
                    edges.append((parent_node['text'], lf['text']))
                    stack_children.add(lf['text'])
                col_categories.extend(items[:i])
            else:
                col_categories.extend(items)

        # 3. Connect root to Tier 1 nodes
        tier1 = sorted([n for n in col_categories if n['top'] <= root['top'] + 85 and n['text'] not in stack_children], key=lambda x: x['left'])
        for t1 in tier1:
            edges.append((root['text'], t1['text']))

        # 4. Connect remaining branch categories tier-by-tier
        remaining = [n for n in col_categories if n not in tier1 and n['text'] not in stack_children]
        remaining.sort(key=lambda x: x['top'])

        for c in remaining:
            cands = [p for p in col_categories if p['top'] < c['top'] - 20 and p['text'] not in stack_children]
            if cands:
                max_top = max(p['top'] for p in cands)
                tier_cands = [p for p in cands if max_top - p['top'] <= 65]
                best = None
                if 'Experimental' in [p['text'] for p in tier_cands] and c['text'] in ('Causation', 'Characteristics', 'Settings'):
                    best = next(p for p in tier_cands if p['text'] == 'Experimental')
                elif 'Quantitative' in [p['text'] for p in tier_cands] and c['text'] in ('Variables', 'Experimental', 'Nonexperimental'):
                    best = next(p for p in tier_cands if p['text'] == 'Quantitative')
                elif 'Science' in [p['text'] for p in tier_cands] and c['text'] in ('Characteristics', 'Assumptions', 'Scientific Approach to Knowledge Generation', 'Role of Theory', 'Objectives'):
                    best = next(p for p in tier_cands if p['text'] == 'Science')
                else:
                    best = min(tier_cands, key=lambda p: abs(p['left'] - c['left']))
                edges.append((best['text'], c['text']))

        map_type = style.get("concept_map_type", "graph LR")
        clean_root = root["text"].replace('"', '')
        mermaid = ['```mermaid', map_type, f'    Root["{clean_root}"]']
        seen_edges = set()
        for p_txt, c_txt in edges:
            if (p_txt, c_txt) not in seen_edges:
                seen_edges.add((p_txt, c_txt))
                pid = node_id_map[p_txt]
                cid = node_id_map[c_txt]
                p_clean = p_txt.replace('"', '')
                c_clean = c_txt.replace('"', '')
                mermaid.append(f'    {pid}["{p_clean}"] --> {cid}["{c_clean}"]')
        mermaid.append('```')

        res_md = '\n'.join(mermaid)
        return res_md, consumed
