import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from behavior import DEFAULTS, REACTIONS, ReactionBag, clamp_position, direction_index, load_settings, save_settings


class BehaviorTests(unittest.TestCase):
    def test_reaction_bag_has_variety_without_repeats(self):
        for seed in range(20):
            bag=ReactionBag(random.Random(seed))
            count = len(REACTIONS) * 10
            choices=[bag.next() for _ in range(count)]
            self.assertTrue(all(a!=b for a,b in zip(choices,choices[1:])))
            for i in range(0,count,len(REACTIONS)):
                self.assertEqual(set(choices[i:i+len(REACTIONS)]),set(REACTIONS))

    def test_directions_match_sprite_contract(self):
        self.assertEqual([direction_index(*p) for p in [(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]],[0,2,4,6,8,10,12,14])

    def test_negative_monitor_coordinates_and_oversized_pet(self):
        self.assertEqual(clamp_position(-3000,-100,240,260,(-1920,0,1920,1080)),(-1920,0))
        self.assertEqual(clamp_position(500,2000,240,260,(-1920,0,1920,1080)),(-240,820))
        self.assertEqual(clamp_position(100,100,400,400,(0,0,200,200)),(0,0))

    def test_corrupt_and_untrusted_settings_do_not_hide_pet(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'settings.json'
            p.write_text('{broken',encoding='utf-8')
            self.assertEqual(load_settings(p),DEFAULTS)
            p.write_text(json.dumps({'scale':9999,'x':10**20,'paused':'yes','topmost':False}),encoding='utf-8')
            got=load_settings(p)
            self.assertEqual(got['scale'],2.0)
            self.assertIsNone(got['x'])
            self.assertIs(got['paused'],False)
            self.assertIs(got['topmost'],False)

    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'settings.json';s=dict(DEFAULTS,x=-500,y=180,scale=1.5)
            save_settings(p,s)
            self.assertEqual(load_settings(p),s)
            self.assertFalse(p.with_suffix('.tmp').exists())

    def test_old_settings_gain_intervals_and_invalid_intervals_are_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'settings.json'
            p.write_text(json.dumps({'roam':True,'follow_mouse':True}),encoding='utf-8')
            old=load_settings(p)
            self.assertEqual((old['idle_interval'],old['walk_interval']),(4,10))
            self.assertTrue(old['roam'] and old['follow_mouse'])
            p.write_text(json.dumps({'idle_interval':-10,'walk_interval':99999}),encoding='utf-8')
            bounded=load_settings(p)
            self.assertEqual((bounded['idle_interval'],bounded['walk_interval']),(2,300))
            p.write_text(json.dumps({'idle_interval':True,'walk_interval':'bad'}),encoding='utf-8')
            self.assertEqual(load_settings(p)['idle_interval'],DEFAULTS['idle_interval'])
            self.assertEqual(load_settings(p)['walk_interval'],DEFAULTS['walk_interval'])


if __name__=='__main__':unittest.main()
