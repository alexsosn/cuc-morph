import tempfile
import unittest
from pathlib import Path

from pipeline.tablet_parsing import PipelineConfig, TabletParsingPipeline


class TabletParsingPipelineTest(unittest.TestCase):
    def test_default_glob_includes_ktu2_family(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            src = root / "cuc_tablets_tsv"
            out = root / "out"
            src.mkdir(parents=True)
            out.mkdir(parents=True)

            (src / "KTU 2.1.tsv").write_text("", encoding="utf-8")

            config = PipelineConfig(
                source_dir=src,
                out_dir=out,
                dulat_db=root / "dulat.sqlite",
                udb_db=root / "udb.sqlite",
                include_existing=False,
            )
            pipeline = TabletParsingPipeline(config=config)
            targets = pipeline.select_targets()

            self.assertEqual([p.name for p in targets], ["KTU 2.1.tsv"])

    def test_select_targets_missing_only(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            src = root / "cuc_tablets_tsv"
            out = root / "out"
            src.mkdir(parents=True)
            out.mkdir(parents=True)

            (src / "KTU 1.1.tsv").write_text("", encoding="utf-8")
            (src / "KTU 1.2.tsv").write_text("", encoding="utf-8")
            (src / "KTU 1.3.tsv").write_text("", encoding="utf-8")
            (out / "KTU 1.1.tsv").write_text("", encoding="utf-8")

            config = PipelineConfig(
                source_dir=src,
                out_dir=out,
                dulat_db=root / "dulat.sqlite",
                udb_db=root / "udb.sqlite",
                include_existing=False,
            )
            pipeline = TabletParsingPipeline(config=config)
            targets = pipeline.select_targets()

            self.assertEqual([p.name for p in targets], ["KTU 1.2.tsv", "KTU 1.3.tsv"])

    def test_select_targets_explicit(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            src = root / "cuc_tablets_tsv"
            out = root / "out"
            src.mkdir(parents=True)
            out.mkdir(parents=True)

            (src / "KTU 1.170.tsv").write_text("", encoding="utf-8")
            (src / "KTU 1.171.tsv").write_text("", encoding="utf-8")

            config = PipelineConfig(
                source_dir=src,
                out_dir=out,
                dulat_db=root / "dulat.sqlite",
                udb_db=root / "udb.sqlite",
                include_existing=False,
            )
            pipeline = TabletParsingPipeline(config=config)
            targets = pipeline.select_targets(explicit_names=["KTU 1.171.tsv", "KTU 1.170.tsv"])

            self.assertEqual([p.name for p in targets], ["KTU 1.170.tsv", "KTU 1.171.tsv"])

    def test_run_dry_run_returns_summary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            src = root / "cuc_tablets_tsv"
            out = root / "out"
            src.mkdir(parents=True)
            out.mkdir(parents=True)
            (src / "KTU 1.180.tsv").write_text("", encoding="utf-8")

            config = PipelineConfig(
                source_dir=src,
                out_dir=out,
                dulat_db=root / "dulat.sqlite",
                udb_db=root / "udb.sqlite",
                include_existing=False,
            )
            pipeline = TabletParsingPipeline(config=config)
            result = pipeline.run(dry_run=True)

            self.assertEqual(result["targets"], ["KTU 1.180.tsv"])
            self.assertEqual(result["target_count"], 1)
            self.assertTrue(result["dry_run"])

    def test_suffix_payload_collapse_runs_after_known_ambiguities(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            src = root / "cuc_tablets_tsv"
            out = root / "out"
            src.mkdir(parents=True)
            out.mkdir(parents=True)

            config = PipelineConfig(
                source_dir=src,
                out_dir=out,
                dulat_db=root / "dulat.sqlite",
                udb_db=root / "udb.sqlite",
                include_existing=False,
            )
            pipeline = TabletParsingPipeline(config=config)
            names = [step.name for step in pipeline._refinement_steps]

            self.assertLess(
                names.index("known-ambiguity-expander"),
                names.index("suffix-payload-collapse"),
            )
            self.assertLess(
                names.index("unwrapped-duplicate-pruner"),
                names.index("l-negation-verb-context"),
            )
            self.assertLess(
                names.index("l-negation-verb-context"),
                names.index("l-functor-vocative-context"),
            )
            self.assertLess(
                names.index("l-functor-vocative-context"),
                names.index("l-kbd-compound-prep"),
            )
            self.assertLess(
                names.index("l-kbd-compound-prep"),
                names.index("ydk-context-disambiguator"),
            )


if __name__ == "__main__":
    unittest.main()
