from __future__ import annotations

import torch
from torch import nn
from torchvision.models import MobileNet_V2_Weights, mobilenet_v2


class FusionClassifier(nn.Module):
    def __init__(
        self,
        metadata_dim: int,
        num_classes: int = 6,
        image_only: bool = False,
        pretrained: bool = True,
    ) -> None:
        super().__init__()
        weights = MobileNet_V2_Weights.DEFAULT if pretrained else None
        backbone = mobilenet_v2(weights=weights)
        self.image_backbone = backbone.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.image_dim = backbone.last_channel
        self.image_only = image_only
        self.metadata_branch = nn.Sequential(
            nn.Linear(metadata_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(64, 32),
            nn.ReLU(),
        )
        combined_dim = self.image_dim if image_only else self.image_dim + 32
        self.classifier = nn.Sequential(
            nn.Linear(combined_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.35),
            nn.Linear(128, num_classes),
        )

    def forward(self, images: torch.Tensor, metadata: torch.Tensor) -> torch.Tensor:
        image_features = self.pool(self.image_backbone(images)).flatten(1)
        if self.image_only:
            fused = image_features
        else:
            fused = torch.cat((image_features, self.metadata_branch(metadata)), dim=1)
        return self.classifier(fused)

    def set_backbone_trainable(self, trainable: bool, last_blocks: int = 3) -> None:
        for parameter in self.image_backbone.parameters():
            parameter.requires_grad = False
        if trainable:
            for block in list(self.image_backbone.children())[-last_blocks:]:
                for parameter in block.parameters():
                    parameter.requires_grad = True
