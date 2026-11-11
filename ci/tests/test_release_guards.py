import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'ci/scripts' / f'{name}.py')
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


backend = module('backend_guard')
plan = module('plan_guard')
bundle = module('bundle')


class BackendTests(unittest.TestCase):
    expected = {'bucket': 'existing-state', 'key': 'echoscript/prod/terraform.tfstate', 'dynamodb_table': 'existing-lock'}

    def test_existing_backend_only(self):
        text = '\n'.join(f'{key} = "{value}"' for key, value in self.expected.items())
        backend.validate(text + '\nregion = "us-west-2"\nencrypt = true', self.expected)

    def test_wrong_state_or_credentials_rejected(self):
        for extra in ['access_key = "test-marker"', 'region = "us-east-1"', 'bucket = "another-state"']:
            with self.assertRaises(ValueError):
                backend.validate(extra, self.expected)


class PlanTests(unittest.TestCase):
    def resource(self, address, actions):
        return {'resource_changes': [{'address': address, 'mode': 'managed', 'change': {'actions': actions, 'after': {'secret': 'DO-NOT-PRINT'}}}]}

    def test_image_release_and_worker_revision_replacement(self):
        for address, actions in [('aws_ecs_express_gateway_service.api', ['update']), ('aws_ecs_task_definition.worker', ['create', 'delete'])]:
            result = plan.summarize(self.resource(address, actions))
            self.assertEqual(result['resource_changes'][0]['actions'], actions)
            self.assertNotIn('DO-NOT-PRINT', json.dumps(result))

    def test_storage_changes_and_resource_deletions_fail_closed(self):
        for address, actions in [('aws_s3_bucket.input', ['delete']), ('aws_dynamodb_table.jobs', ['update']), ('aws_ecs_express_gateway_service.api', ['delete', 'create'])]:
            with self.assertRaises(ValueError):
                plan.summarize(self.resource(address, actions))


class BundleTests(unittest.TestCase):
    def archive(self, destination, name, text=b'<html>previous release</html>'):
        with tarfile.open(destination, 'w:gz') as archive:
            entry = tarfile.TarInfo(name)
            entry.size = len(text)
            archive.addfile(entry, io.BytesIO(text))

    def test_restores_previous_bundle_without_rebuilding_or_touching_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'previous.tar.gz'
            self.archive(archive, 'index.html')
            before = bundle.digest(archive)
            bundle.extract(archive, root / 'restored')
            self.assertEqual((root / 'restored/index.html').read_text(), '<html>previous release</html>')
            self.assertEqual(before, bundle.digest(archive))

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'unsafe.tar.gz'
            self.archive(archive, '../outside')
            with self.assertRaises(ValueError):
                bundle.extract(archive, root / 'restored')
            self.assertFalse((root / 'outside').exists())


if __name__ == '__main__':
    unittest.main()
