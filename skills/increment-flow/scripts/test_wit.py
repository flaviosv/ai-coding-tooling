"""Behavioral checks for title-only creation and later description completion."""
import contextlib
import copy
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('wit', Path(__file__).with_name('wit.py'))
wit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wit)
DESCRIPTION = '\n'.join(f'{label} Conteúdo completo.' for label in wit.DESCRIPTION_LABELS)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='increment-flow-test-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / '005-tres-fatias'
        self.folder.mkdir()
        self.calls = []
        self.items = {'50': self.item(50, 'User Story')}
        self.next_id = 100
        self.fake = patch.object(wit, 'az', side_effect=self.az)
        self.fake.start()
        self.addCleanup(self.fake.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def item(self, number, kind):
        return {'id': number, 'fields': {'System.TeamProject': 'SYS-COE',
                'System.WorkItemType': kind, 'System.State': 'New'},
                '_links': {'html': {'href': f'https://example.test/_workitems/edit/{number}'}}}

    def az(self, *args, org=None):
        self.calls.append(args)
        if args[:2] == ('work-item', 'create'):
            number = self.next_id
            self.next_id += 1
            item = self.item(number, args[args.index('--type') + 1])
            if '--description' in args:
                item['fields']['System.Description'] = args[args.index('--description') + 1]
            self.items[str(number)] = item
            return copy.deepcopy(item)
        if args[:3] == ('work-item', 'relation', 'add'):
            return {}
        item = self.items[args[args.index('--id') + 1]]
        if args[:2] == ('work-item', 'update'):
            if '--description' in args:
                item['fields']['System.Description'] = args[args.index('--description') + 1]
            if '--title' in args:
                item['fields']['System.Title'] = args[args.index('--title') + 1]
            if '--state' in args:
                item['fields']['System.State'] = args[args.index('--state') + 1]
        return copy.deepcopy(item)

    def test_title_only_create_then_complete_same_active_task(self):
        wit.cmd_create(self.folder, '50', 'Migrar agentes de pesquisa', '')
        create = next(c for c in self.calls if c[:2] == ('work-item', 'create'))
        self.assertNotIn('--description', create)
        self.assertTrue(any(c[:3] == ('work-item', 'relation', 'add') for c in self.calls))
        wit.cmd_state(self.folder, 'Active')
        wit.cmd_update(self.folder, DESCRIPTION)
        wit.cmd_update(self.folder, DESCRIPTION)
        rows = wit.read_wit(self.folder / 'wit.md')
        self.assertIn('#100', rows['Task'])
        self.assertIn('#50', rows['User Story'])
        self.assertEqual(rows['State'], 'Active')
        self.assertEqual(sum(c[:2] == ('work-item', 'create') for c in self.calls), 1)
        self.assertEqual(sum(c[:2] == ('work-item', 'update') and '--description' in c for c in self.calls), 1)

    def test_cli_response_without_html_links(self):
        for item in self.items.values():
            item.pop('_links')
            item['url'] = f"https://dev.azure.com/example/project/_apis/wit/workItems/{item['id']}"
        original = self.item
        def cli_item(number, kind):
            item = original(number, kind)
            item.pop('_links')
            item['url'] = f"https://dev.azure.com/example/project/_apis/wit/workItems/{number}"
            return item
        self.item = cli_item
        wit.cmd_create(self.folder, '50', 'Migrar agentes', '')
        rows = wit.read_wit(self.folder / 'wit.md')
        self.assertIn('/_workitems/edit/100', rows['Task'])
        self.assertIn('/_workitems/edit/50', rows['User Story'])

    def test_create_without_parent(self):
        wit.cmd_create(self.folder, None, 'Migrar agentes', '', 'SYS-COE')
        rows = wit.read_wit(self.folder / 'wit.md')
        self.assertEqual(rows['User Story'], 'none')
        self.assertIn('#100', rows['Task'])
        self.assertFalse(any(c[:3] == ('work-item', 'relation', 'add') for c in self.calls))

    def test_partial_description_and_empty_feature_are_rejected_before_write(self):
        for kind, body in [('Task', 'Texto parcial'), ('Feature', ''), ('User Story', '')]:
            with self.subTest(kind=kind), self.assertRaises(SystemExit):
                wit.make_item(kind, 'Trabalho', body, None, 'SYS-COE', None)
        self.assertEqual(self.calls, [])

    def test_existing_task_cannot_be_recreated(self):
        wit.cmd_create(self.folder, '50', 'Migrar agentes', DESCRIPTION)
        with self.assertRaises(SystemExit):
            wit.cmd_create(self.folder, '50', 'Migrar agentes', '')
        self.assertEqual(sum(c[:2] == ('work-item', 'create') for c in self.calls), 1)

    def test_update_can_retitle_and_rewrite_changed_scope(self):
        wit.cmd_create(self.folder, '50', 'Migrar agentes de pesquisa', '')
        wit.cmd_update(self.folder, DESCRIPTION, 'Migrar agentes e fontes de pesquisa')
        task = self.items['100']['fields']
        self.assertEqual(task['System.Title'], 'Migrar agentes e fontes de pesquisa')
        self.assertIn('Conteúdo completo.', task['System.Description'])
        wit.cmd_update(self.folder, DESCRIPTION, 'Migrar agentes e fontes de pesquisa')
        self.assertEqual(sum(c[:2] == ('work-item', 'update') and '--title' in c for c in self.calls), 1)

    def test_update_rejects_missing_task_and_incomplete_description(self):
        with self.assertRaises(SystemExit):
            wit.cmd_update(self.folder, DESCRIPTION)
        wit.cmd_create(self.folder, '50', 'Migrar agentes', '')
        with self.assertRaises(SystemExit):
            wit.cmd_update(self.folder, '')
        self.assertFalse(any('--description' in c for c in self.calls))

    def test_update_detects_readback_mismatch(self):
        wit.cmd_create(self.folder, '50', 'Migrar agentes', '')
        def stale(*args, org=None):
            item = self.az(*args, org=org)
            if args[:2] == ('work-item', 'show'):
                item['fields'].pop('System.Description', None)
            return item
        with patch.object(wit, 'az', side_effect=stale), self.assertRaises(SystemExit):
            wit.cmd_update(self.folder, DESCRIPTION)


if __name__ == '__main__':
    unittest.main()
