import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from selection_rules import assess,normalize
from style_selector import select

class SelectionTest(unittest.TestCase):
    def test_shadow_requires_observed_structure(self):
        style={'id':'shadow','origin':'original','fidelity':'medium','contract':{'needsAny':['strong-shadows','reflections'],'bestFeatures':['object','strong-shadows']}}
        self.assertFalse(assess(style,['object','low-contrast'])['compatible'])
        self.assertTrue(assess(style,['object','strong-shadows'])['compatible'])
    def test_preservation_cannot_be_overridden_by_many_positive_tags(self):
        style={'id':'redraw','origin':'original','fidelity':'medium','contract':{'bestFeatures':['person','strong-geometry','strong-color']}}
        self.assertFalse(assess(style,['person','strong-geometry','strong-color','exact-pixels'])['compatible'])
    def test_empty_matches_do_not_become_recommendations(self):
        for mode in ('recommend','random'):
            self.assertEqual(select([{'id':'a','installed':True,'best':['food']}],mode,{'landscape'},3),[])
    def test_family_diversity_and_manual_exclusion(self):
        source=[{'id':x,'installed':True,'best':['plant']} for x in ['minimal-zine','muted-zine','photo-revival']]
        source.insert(0,{'id':'jiuerli-sketch','installed':True,'manualOnly':True,'best':['plant']})
        self.assertEqual([s['id'] for s in select(source,'recommend',{'plant'},2)],['minimal-zine','photo-revival'])
    def test_subject_language_normalization(self):
        self.assertEqual(normalize(['植物','strong-silhouette','exact-pixels']),{'plant','clear-silhouette','faithful-photo'})
    def test_input_count_blocks_single_photo_workflow(self):
        style={'id':'single','installed':True,'contract':{'inputCount':{'min':1,'max':1},'bestFeatures':['plant']}}
        self.assertEqual(select([style],'recommend',{'plant'},3,input_count=2),[])
        self.assertEqual(len(select([style],'recommend',{'plant'},3,input_count=1)),1)
