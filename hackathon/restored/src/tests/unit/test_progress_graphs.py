"""Tests for graph fold GPU progress bar events in _on_tuning_hpo.

Validates:
1. graph_fold_start creates per-GPU subtask bars
2. graph_fold_epoch updates the correct GPU's progress bar
3. graph_fold_complete removes all GPU subtask bars
4. No bars created when no graph_fold_start event is received
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

from volforecast.cli.progress import StageProgress


def _make_handler():
    """Build a minimal _on_tuning_hpo closure with graph_fold_* handling.

    Returns (handler_fn, sp, graph_gpu_keys) so tests can inspect state.
    """
    sp = MagicMock(spec=StageProgress)
    # Track subtasks like the real StageProgress
    _subtask_counter = 0
    _subtasks: dict[str, int] = {}  # key -> fake task_id

    def _add_subtask(total=None, description="", *, indent=1):
        nonlocal _subtask_counter
        _subtask_counter += 1
        key = f"sub:{description}"
        _subtasks[key] = _subtask_counter
        return key

    def _remove_subtask(key):
        _subtasks.pop(key, None)

    sp.add_subtask.side_effect = _add_subtask
    sp.remove_subtask.side_effect = _remove_subtask
    sp._subtasks = _subtasks
    sp._progress = MagicMock()

    _hpo_gpu_keys: dict[int, str] = {}
    _graph_gpu_keys: dict[int, str] = {}
    _progress_lock = threading.Lock()

    def handler(event: dict) -> None:
        event_type = event.get("type", "")

        with _progress_lock:
            if event_type == "graph_fold_start":
                n_gpus_active = event["n_gpus"]
                max_epochs = event.get("max_epochs", 200)
                for gpu_id in range(n_gpus_active):
                    key = sp.add_subtask(
                        total=max_epochs,
                        description=f"GPU {gpu_id}: starting",
                        indent=2,
                    )
                    _graph_gpu_keys[gpu_id] = key

            elif event_type == "graph_fold_epoch":
                device_id = event.get("device_id")
                fold = event.get("fold")
                epoch = event["epoch"]
                max_epochs = event["max_epochs"]
                if device_id is not None and device_id in _graph_gpu_keys:
                    task_id = sp._subtasks[_graph_gpu_keys[device_id]]
                    prefix = "    " + "  └─ "
                    sp._progress.update(
                        task_id,
                        description=f"{prefix}GPU {device_id}: fold {fold} · epoch {epoch}/{max_epochs}",
                        completed=epoch,
                        total=max_epochs,
                    )

            elif event_type == "graph_fold_complete":
                for key in list(_graph_gpu_keys.values()):
                    sp.remove_subtask(key)
                _graph_gpu_keys.clear()

    return handler, sp, _graph_gpu_keys


class TestGraphFoldProgressEvents:
    """Test graph fold GPU progress bar event handling."""

    def test_graph_fold_start_creates_gpu_subtasks(self):
        """graph_fold_start event creates per-GPU subtask bars."""
        handler, sp, gpu_keys = _make_handler()

        handler({"type": "graph_fold_start", "n_gpus": 4, "max_epochs": 200})

        assert sp.add_subtask.call_count == 4
        assert len(gpu_keys) == 4
        for gpu_id in range(4):
            assert gpu_id in gpu_keys
        # Verify indent=2 was passed
        for call in sp.add_subtask.call_args_list:
            assert call.kwargs.get("indent") == 2 or call[1].get("indent") == 2

    def test_graph_fold_start_uses_max_epochs_as_total(self):
        """graph_fold_start passes max_epochs as the subtask total."""
        handler, sp, _ = _make_handler()

        handler({"type": "graph_fold_start", "n_gpus": 2, "max_epochs": 300})

        for call in sp.add_subtask.call_args_list:
            assert call.kwargs.get("total") == 300 or call[0][0] == 300

    def test_graph_fold_epoch_updates_gpu_bar(self):
        """graph_fold_epoch updates the correct GPU's progress bar."""
        handler, sp, gpu_keys = _make_handler()

        handler({"type": "graph_fold_start", "n_gpus": 4, "max_epochs": 200})
        handler({
            "type": "graph_fold_epoch",
            "device_id": 0,
            "fold": 3,
            "epoch": 50,
            "max_epochs": 200,
        })

        sp._progress.update.assert_called_once()
        call_kwargs = sp._progress.update.call_args
        desc = call_kwargs.kwargs.get("description") or call_kwargs[1].get("description", "")
        assert "GPU 0" in desc
        assert "fold 3" in desc
        assert "50/200" in desc
        assert call_kwargs.kwargs.get("completed") == 50 or call_kwargs[1].get("completed") == 50

    def test_graph_fold_epoch_updates_correct_gpu(self):
        """graph_fold_epoch targets the right GPU when multiple are active."""
        handler, sp, gpu_keys = _make_handler()

        handler({"type": "graph_fold_start", "n_gpus": 4, "max_epochs": 200})
        sp._progress.reset_mock()

        handler({
            "type": "graph_fold_epoch",
            "device_id": 2,
            "fold": 7,
            "epoch": 100,
            "max_epochs": 200,
        })

        call_kwargs = sp._progress.update.call_args
        desc = call_kwargs.kwargs.get("description") or call_kwargs[1].get("description", "")
        assert "GPU 2" in desc
        assert "fold 7" in desc

    def test_graph_fold_epoch_ignores_unknown_device(self):
        """graph_fold_epoch with unknown device_id is silently ignored."""
        handler, sp, _ = _make_handler()

        handler({"type": "graph_fold_start", "n_gpus": 2, "max_epochs": 200})
        sp._progress.reset_mock()

        handler({
            "type": "graph_fold_epoch",
            "device_id": 99,
            "fold": 1,
            "epoch": 10,
            "max_epochs": 200,
        })

        sp._progress.update.assert_not_called()

    def test_graph_fold_epoch_ignores_none_device(self):
        """graph_fold_epoch with device_id=None is silently ignored."""
        handler, sp, _ = _make_handler()

        handler({"type": "graph_fold_start", "n_gpus": 2, "max_epochs": 200})
        sp._progress.reset_mock()

        handler({
            "type": "graph_fold_epoch",
            "device_id": None,
            "fold": 1,
            "epoch": 10,
            "max_epochs": 200,
        })

        sp._progress.update.assert_not_called()

    def test_graph_fold_complete_removes_bars(self):
        """graph_fold_complete removes all GPU subtask bars."""
        handler, sp, gpu_keys = _make_handler()

        handler({"type": "graph_fold_start", "n_gpus": 4, "max_epochs": 200})
        handler({"type": "graph_fold_complete"})

        assert sp.remove_subtask.call_count == 4
        assert len(gpu_keys) == 0

    def test_graph_fold_complete_idempotent(self):
        """graph_fold_complete on empty state does nothing."""
        handler, sp, gpu_keys = _make_handler()

        handler({"type": "graph_fold_complete"})

        sp.remove_subtask.assert_not_called()
        assert len(gpu_keys) == 0

    def test_sequential_path_no_bars(self):
        """No graph_fold_start event means no bars created (sequential path)."""
        handler, sp, gpu_keys = _make_handler()

        # Only epoch events, no start — should be ignored
        handler({
            "type": "graph_fold_epoch",
            "device_id": 0,
            "fold": 1,
            "epoch": 10,
            "max_epochs": 200,
        })

        sp.add_subtask.assert_not_called()
        sp._progress.update.assert_not_called()
        assert len(gpu_keys) == 0

    def test_full_lifecycle(self):
        """Full lifecycle: start → multiple epochs → complete."""
        handler, sp, gpu_keys = _make_handler()

        handler({"type": "graph_fold_start", "n_gpus": 2, "max_epochs": 100})
        assert len(gpu_keys) == 2

        for epoch in range(1, 11):
            handler({
                "type": "graph_fold_epoch",
                "device_id": 0,
                "fold": 1,
                "epoch": epoch,
                "max_epochs": 100,
            })
            handler({
                "type": "graph_fold_epoch",
                "device_id": 1,
                "fold": 2,
                "epoch": epoch,
                "max_epochs": 100,
            })

        assert sp._progress.update.call_count == 20

        handler({"type": "graph_fold_complete"})
        assert len(gpu_keys) == 0
        assert sp.remove_subtask.call_count == 2
