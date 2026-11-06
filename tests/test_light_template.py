import unittest

from nl2traj.light_template import (
    check_light_template,
    extract_light_template,
    format_template_emphasis,
    template_similarity,
)


class LightTemplateTests(unittest.TestCase):
    def test_emphasis_extracts_roles_without_generating_sql(self):
        template = extract_light_template("晚高峰从西湖区出发的轨迹平均速度")
        emphasis = format_template_emphasis(template)
        self.assertEqual(template.time_role, "departure")
        self.assertTrue(template.origin)
        self.assertIn("time_role: departure", emphasis)

    def test_single_row_check_requires_deterministic_order(self):
        template = extract_light_template("查询正在运行的一条轨迹的位置")
        sql = "SELECT trip_id, ST_AsText(valueAtTimestamp(trip_trajectory, now())) FROM trips LIMIT 1;"
        issues = check_light_template(template, sql)
        self.assertTrue(any("ORDER BY" in issue for issue in issues))

    def test_template_similarity_prefers_same_time_role(self):
        target = extract_light_template("晚高峰出发的轨迹数量")
        departure = extract_light_template("早高峰出发的轨迹数量")
        arrival = extract_light_template("晚高峰到达的轨迹数量")
        self.assertGreater(template_similarity(target, departure), template_similarity(target, arrival))


if __name__ == "__main__":
    unittest.main()
