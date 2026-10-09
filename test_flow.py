import itertools
import unittest
from unittest.mock import patch
import narrative_flow as nf

class FlowTest(unittest.TestCase):
    @patch('narrative_flow.time.monotonic', return_value=100.0)
    def test_every_order_and_target(self, clock):
        count=0
        for order in itertools.permutations(nf.FOUNDERS, 3):
            for target in set(nf.FOUNDERS)-set(order):
                s=nf.new()
                for idx, aid in enumerate(order):
                    for turn in range(4):
                        self.assertTrue(nf.home_dialogue(s,aid))
                        self.assertEqual(len(s['met']),idx)
                    self.assertTrue(nf.home_dialogue(s,aid))
                    self.assertEqual(len(s['met']),idx+1)
                    self.assertFalse(nf.home_dialogue(s,aid))
                    if idx < 2:
                        self.assertTrue(s['referral_pending'])
                        self.assertFalse(nf.refer(s,aid,aid,'invalid'))
                        self.assertTrue(nf.refer(s,aid,order[idx+1],'alleanza'))
                self.assertEqual(s['phase'],'brago_video')
                nf.continue_video(s)
                self.assertFalse(nf.kidnap(s,order[0]))
                self.assertTrue(nf.kidnap(s,target))
                self.assertEqual({s['captive'],s['gatekeeper']},set(nf.FOUNDERS)-set(order))
                self.assertFalse(nf.grant(s,s['gatekeeper']))
                for aid in nf.FOUNDERS: nf.bar_dialogue(s,aid)
                for aid in nf.FOUNDERS:
                    if aid!=s['gatekeeper']: self.assertFalse(nf.grant(s,aid))
                self.assertTrue(nf.grant(s,s['gatekeeper']))
                s=nf.restore(nf.snapshot(s))
                self.assertTrue(nf.deliver(s))
                self.assertEqual(s['phase'],'vittoria')
                count+=1
        self.assertEqual(count,120)

    def test_clock_pause_expiry(self):
        s=nf.new(now=0)
        nf.pause(s,True,now=100)
        nf.update_clock(s,now=10000)
        self.assertEqual(s['elapsed'],100)
        nf.pause(s,False,now=10000)
        nf.update_clock(s,now=11100)
        self.assertEqual(s['phase'],'sconfitta')
        self.assertFalse(nf.deliver(s))

    @patch('narrative_flow.time.monotonic', return_value=100.0)
    def test_cheats(self, clock):
        s=nf.new()
        for phase in ('brago_video','sequestro','lizzie_bar','backstage','vittoria'):
            nf.cheat(s)
            self.assertEqual(s['phase'],phase)
            nf.restore(nf.snapshot(s))
        self.assertTrue(s['cheated'])

    @patch('narrative_flow.time.monotonic', return_value=100.0)
    def test_pause_blocks_actions(self, clock):
        s=nf.new(); nf.pause(s,True)
        self.assertFalse(nf.home_dialogue(s,'klaus'))
        self.assertEqual(s['met'],[])

if __name__=='__main__': unittest.main()
