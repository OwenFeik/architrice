import os
import tempfile
import unittest

import architrice

from . import mockapi


class TestIntegration(unittest.TestCase):
    TEST_USER_NAME = "Test"
    TEST_DECK_NAME = "Test Deck"
    TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp()
        print("Test output: " + cls.directory)

        architrice.utils._DATA_DIR = architrice.utils.DATA_DIR
        architrice.utils.DATA_DIR = os.path.join(cls.directory, "architrice")
        architrice.database.init()
        mockapi.mock()

    @classmethod
    def tearDown(cls):
        architrice.utils.DATA_DIR = architrice.utils._DATA_DIR
        architrice.database.close()
        mockapi.stop()

    def verifyOutput(self, profile):
        for output in profile.outputs:
            file_name = output.target.create_file_name(
                TestIntegration.TEST_DECK_NAME
            )
            created_file = os.path.join(
                output.output_dir.path,
                file_name,
            )

            failure_info = (
                f"for source {profile.source.short} and "
                f"target {output.target.short}."
            )

            self.assertTrue(
                os.path.exists(created_file),
                f"Deck file not created {failure_info}",
            )
            with open(created_file) as f:
                created_text = f.read()

            with open(
                os.path.join(
                    TestIntegration.TEST_DATA_DIR,
                    output.target.short,
                    file_name,
                )
            ) as f:
                correct_text = f.read()

            self.assertEqual(
                created_text,
                correct_text,
                f"Bad deck file {failure_info}: {created_file}",
            )

    def testIntegration(self):
        # Tests by creating a profile for each source, with an output for each
        # target and downloading the test deck for each source-target
        # combination, verifying that the decks were downloaded.

        cache = architrice.caching.Cache.load()

        deck_dir = os.path.join(TestIntegration.directory, "out")

        for source in architrice.sources.get_all():
            self.assertTrue(
                source.verify_user(TestIntegration.TEST_USER_NAME),
                f"User verification failed for source {source.short}",
            )
            profile = cache.build_profile(
                source, TestIntegration.TEST_USER_NAME
            )

            for target in architrice.targets.get_all():
                cache.build_output(
                    profile,
                    target,
                    os.path.join(deck_dir, source.short, target.short),
                    True,
                )

            profile.download_all()
            self.verifyOutput(profile)


if __name__ == "__main__":
    unittest.main()
