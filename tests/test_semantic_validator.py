import unittest

from nl2traj.error_diagnostics import diagnose_execution_error, diagnose_semantic_issues
from nl2traj.semantic_validator import validate_candidate


class SemanticValidatorTests(unittest.TestCase):
    def test_peak_departure_rejects_process_clipping(self):
        report = validate_candidate(
            "晚高峰平均速度最低的前 5 条轨迹",
            "SELECT trip_id FROM trips WHERE atTime(trip_trajectory, tstzspan('[2020-01-01 17:00+08, 2020-01-01 19:00+08)')) IS NOT NULL ORDER BY trip_id LIMIT 5;",
            "[[1]]",
        )
        self.assertIn("peak_scope_wrong", {x.code for x in report.blocking_issues})
        self.assertIn("peak_departure_missing", {x.code for x in report.blocking_issues})

    def test_peak_arrival_uses_end_timestamp(self):
        report = validate_candidate(
            "查询晚高峰到达上城区的轨迹数量",
            "SELECT COUNT(*) FROM trips WHERE endTimestamp(trip_trajectory)::time >= TIME '17:00';",
            "[[1]]",
        )
        self.assertNotIn("peak_arrival_missing", {x.code for x in report.blocking_issues})

    def test_grouped_average_speed_requires_avg(self):
        report = validate_candidate(
            "查询各日期中平均速度最高的一天",
            "SELECT trip_date, SUM(distance) / SUM(seconds) FROM x GROUP BY trip_date ORDER BY 2 DESC LIMIT 1;",
            '[["2020-01-01", 1]]',
        )
        self.assertIn("average_grain_wrong", {x.code for x in report.blocking_issues})

    def test_ratio_rejects_percentage_scale_and_requires_rounding(self):
        report = validate_candidate(
            "查询目标轨迹占比（保留四位小数）",
            "SELECT COUNT(*)::numeric / NULLIF(COUNT(*), 0) * 100 FROM trips;",
            "[[20.28]]",
        )
        codes = {x.code for x in report.blocking_issues}
        self.assertIn("ratio_scale_wrong", codes)
        self.assertIn("ratio_rounding_missing", codes)

    def test_position_output_contract(self):
        report = validate_candidate(
            "查询 2020-01-06 10:00 正在运行的一条轨迹的位置。",
            "SELECT valueAtTimestamp(trip_trajectory, TIMESTAMPTZ '2020-01-06 10:00+08') FROM trips LIMIT 1;",
            '[["hex"]]',
        )
        codes = {x.code for x in report.blocking_issues}
        self.assertIn("output_trip_id_missing", codes)
        self.assertIn("output_geometry_unserialized", codes)

    def test_passing_rejects_covered_by_only(self):
        report = validate_candidate(
            "查询路径经过西湖区的轨迹数量",
            "SELECT COUNT(*) FROM trips t JOIN districts d ON ST_CoveredBy(trajectory(t.trip_trajectory), d.geometry);",
            "[[1]]",
        )
        self.assertIn("passing_predicate_wrong", {x.code for x in report.blocking_issues})

    def test_negative_destination_must_bind_actual_district(self):
        report = validate_candidate(
            "查询终点不在萧山区的轨迹数量",
            "SELECT COUNT(*) FROM trips t WHERE NOT ST_Covers((SELECT geometry FROM districts WHERE name='萧山区'), endValue(t.trip_trajectory));",
            "[[1]]",
        )
        self.assertIn("negative_destination_unbound", {x.code for x in report.blocking_issues})

    def test_endpoint_and_passing_roles_are_checked(self):
        report = validate_candidate(
            "查询从上城区出发并经过西湖区的轨迹数量",
            "SELECT COUNT(*) FROM trips;",
            "[[3]]",
        )
        self.assertFalse(report.passed)
        self.assertEqual(
            {issue.code for issue in report.blocking_issues},
            {"origin_missing", "passing_missing", "passing_predicate_wrong", "light_template_mismatch"},
        )

    def test_correct_endpoint_and_passing_query_passes(self):
        report = validate_candidate(
            "查询从上城区出发并经过西湖区的轨迹数量",
            """SELECT COUNT(*) FROM trips t JOIN districts s
            ON ST_Covers(s.geometry, startValue(t.trip_trajectory))
            JOIN districts p ON ST_Intersects(trajectory(t.trip_trajectory), p.geometry);""",
            "[[3]]",
        )
        self.assertTrue(report.passed)

    def test_local_metric_requires_clipping(self):
        report = validate_candidate(
            "计算西湖区内的总移动长度",
            "SELECT SUM(ST_Length(trajectory(trip_trajectory))) FROM trips;",
            "[[123]]",
        )
        self.assertIn("local_space_missing", {x.code for x in report.issues})

    def test_execution_error_is_typed(self):
        diagnosis = diagnose_execution_error('column "foo" does not exist')
        self.assertEqual(diagnosis.category, "schema_mismatch")
        self.assertIn("repair_scope", diagnosis.to_feedback("column foo"))

    def test_semantic_error_is_typed(self):
        report = validate_candidate("起点在西湖区的轨迹数量", "SELECT COUNT(*) FROM trips;", "[[1]]")
        diagnosis = diagnose_semantic_issues(report.issues)
        self.assertEqual(diagnosis.category, "wrong_spatial_semantics")


if __name__ == "__main__":
    unittest.main()
