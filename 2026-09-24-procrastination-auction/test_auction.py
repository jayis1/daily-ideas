import unittest
import random

from auction import Task, auction, parse_task


class AuctionTests(unittest.TestCase):
    def test_parse_task(self):
        task = parse_task("write a haiku,8,3,5")
        self.assertEqual(task.name, "write a haiku")
        self.assertEqual(task.bid, 71)

    def test_parse_task_rejects_bad_ranges(self):
        with self.assertRaises(ValueError):
            parse_task("too brave,11,2,5")
        with self.assertRaises(ValueError):
            parse_task("missing fields,4,4")

    def test_auction_never_spends_more_than_budget(self):
        tasks = [Task("a", 10, 10, 20), Task("b", 1, 1, 20)]
        result = auction(tasks, 7, random.Random(2))
        self.assertEqual(sum(result["allocations"].values()), 7)
        self.assertEqual(result["unused_minutes"], 0)

    def test_auction_does_not_mutate_task_definitions(self):
        tasks = [Task("a", 5, 5, 10)]
        auction(tasks, 5, random.Random(3))
        self.assertEqual(tasks[0].minutes, 10)

    def test_seed_makes_rounds_repeatable(self):
        def run():
            return auction([Task("a", 5, 5, 10), Task("b", 5, 5, 10)], 10,
                           random.Random(11))
        self.assertEqual(run(), run())

    def test_custom_round_size_is_respected(self):
        result = auction([Task("a", 10, 10, 10), Task("b", 1, 1, 10)], 4,
                         random.Random(1), round_minutes=2)
        self.assertEqual([round["minutes"] for round in result["rounds"]], [2, 2])

    def test_duplicate_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            auction([Task("same", 5, 5, 5), Task("same", 4, 4, 5)], 5,
                    random.Random(1))


if __name__ == "__main__":
    unittest.main()
