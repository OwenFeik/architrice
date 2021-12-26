import os
import tempfile
import unittest

import architrice

from . import mockapi


class TestIntegration(unittest.TestCase):
    TEST_USER_NAME = "Test"
    TEST_DECK_NAME = "Test Deck"

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp()
        architrice.utils._DATA_DIR = architrice.utils.DATA_DIR
        architrice.utils.DATA_DIR = os.path.join(cls.directory, "architrice")
        architrice.database.init()
        mockapi.mock()

    @classmethod
    def tearDown(cls):
        architrice.utils.DATA_DIR = architrice.utils._DATA_DIR
        architrice.database.close()
        mockapi.stop()

    def testIntegration(self):
        # Tests by creating a profile for each source, with an output for each
        # target and downloading the test deck for each source-target
        # combination, verifying that the decks were downloaded.

        cache = architrice.caching.Cache.load()

        deck_dir = os.path.join(TestIntegration.directory, "out")

        for source in architrice.sources.get_all():
            self.assertTrue(source.verify_user(TestIntegration.TEST_USER_NAME))
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

            for output in profile.outputs:
                self.assertTrue(
                    os.path.exists(
                        os.path.join(
                            output.output_dir.path,
                            output.target.create_file_name(
                                TestIntegration.TEST_DECK_NAME
                            ),
                        )
                    )
                )


if __name__ == "__main__":
    unittest.main()
