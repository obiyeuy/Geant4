#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Train EfficientNet with R-value based 3-channel tensor input."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torch.utils.data import WeightedRandomSampler
from torchvision.models import efficientnet_b0


class NpyFeatureDataset(Dataset):
    def __init__(self, split_root: Path):
        self.items: List[Tuple[Path, int]] = []
        for class_dir in sorted(split_root.glob("class_*")):
            if not class_dir.is_dir():
                continue
            class_id = int(class_dir.name.split("_")[-1])
            for sample_dir in sorted(class_dir.glob("*")):
                input_path = sample_dir / "input.npy"
                if input_path.exists():
                    self.items.append((input_path, class_id))
        if not self.items:
            raise RuntimeError(f"No samples found under split: {split_root}")

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        path, label = self.items[idx]
        x = np.load(path).astype(np.float32)  # [3, H, W]
        return torch.from_numpy(x), torch.tensor(label, dtype=torch.long)


def _evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[float, float]:
    model.eval()
    loss_fn = nn.CrossEntropyLoss()
    total = 0
    loss_sum = 0.0
    correct = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)
            logits = model(x)
            loss = loss_fn(logits, y)
            loss_sum += float(loss.item()) * y.size(0)
            pred = logits.argmax(dim=1)
            correct += int((pred == y).sum().item())
            total += y.size(0)
    return loss_sum / max(total, 1), correct / max(total, 1)


def train(
    dataset_root: Path,
    out_dir: Path,
    epochs: int,
    batch_size: int,
    lr: float,
    num_workers: int,
    balance_mode: str,
) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_set = NpyFeatureDataset(dataset_root / "train")
    val_set = NpyFeatureDataset(dataset_root / "val")
    test_set = NpyFeatureDataset(dataset_root / "test")

    label_counts = Counter(int(label) for _, label in train_set.items)
    labels_sorted = sorted(label_counts.keys())
    class_weights = None
    if labels_sorted:
        # Inverse-frequency weighting: minority class gets larger weight.
        inv = torch.tensor([1.0 / max(label_counts[c], 1) for c in labels_sorted], dtype=torch.float32)
        inv = inv / inv.mean()
        max_class_id = max(labels_sorted)
        class_weights = torch.ones(max_class_id + 1, dtype=torch.float32)
        for idx, class_id in enumerate(labels_sorted):
            class_weights[class_id] = inv[idx]

    sampler = None
    if balance_mode in ("sampler", "both"):
        sample_weights = torch.tensor(
            [1.0 / max(label_counts[int(label)], 1) for _, label in train_set.items],
            dtype=torch.double,
        )
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True,
        )

    train_loader = DataLoader(
        train_set,
        batch_size=batch_size,
        shuffle=(sampler is None),
        sampler=sampler,
        num_workers=num_workers,
    )
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    model = efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    model = model.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = (
        nn.CrossEntropyLoss(weight=class_weights.to(device))
        if (class_weights is not None and balance_mode in ("class_weight", "both"))
        else nn.CrossEntropyLoss()
    )

    history = []
    best_val_acc = -1.0
    out_dir.mkdir(parents=True, exist_ok=True)
    best_path = out_dir / "best_model.pt"

    for epoch in range(1, epochs + 1):
        model.train()
        total = 0
        loss_sum = 0.0
        correct = 0
        for x, y in train_loader:
            x = x.to(device)
            y = y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = loss_fn(logits, y)
            loss.backward()
            optimizer.step()

            loss_sum += float(loss.item()) * y.size(0)
            pred = logits.argmax(dim=1)
            correct += int((pred == y).sum().item())
            total += y.size(0)

        train_loss = loss_sum / max(total, 1)
        train_acc = correct / max(total, 1)
        val_loss, val_acc = _evaluate(model, val_loader, device)

        row = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_acc": train_acc,
            "val_loss": val_loss,
            "val_acc": val_acc,
        }
        history.append(row)
        print(
            f"[Epoch {epoch:03d}] "
            f"train_loss={train_loss:.4f}, train_acc={train_acc:.4f}, "
            f"val_loss={val_loss:.4f}, val_acc={val_acc:.4f}"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), best_path)

    model.load_state_dict(torch.load(best_path, map_location=device))
    test_loss, test_acc = _evaluate(model, test_loader, device)

    metrics = {
        "best_val_acc": best_val_acc,
        "test_loss": test_loss,
        "test_acc": test_acc,
        "epochs": epochs,
        "batch_size": batch_size,
        "lr": lr,
        "device": str(device),
        "train_size": len(train_set),
        "val_size": len(val_set),
        "test_size": len(test_set),
        "balance_mode": balance_mode,
        "train_class_counts": {str(k): int(v) for k, v in sorted(label_counts.items())},
        "train_class_weights": (
            [float(class_weights[i]) for i in range(len(class_weights))]
            if class_weights is not None
            else None
        ),
    }
    with (out_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with (out_dir / "history.json").open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    print("Training complete.")
    print(f"Best model: {best_path}")
    print(f"Test accuracy: {test_acc:.4f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train EfficientNet on R-value dataset")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("data/processed/r_value_dataset"),
        help="Dataset root generated by build_dataset.py",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("experiments/efficientnet_rvalue"),
        help="Experiment output directory",
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument(
        "--balance-mode",
        type=str,
        default="both",
        choices=["none", "class_weight", "sampler", "both"],
        help="Class balancing strategy for imbalanced training sets.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train(
        dataset_root=args.dataset_root,
        out_dir=args.out_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        num_workers=args.num_workers,
        balance_mode=args.balance_mode,
    )


if __name__ == "__main__":
    main()
