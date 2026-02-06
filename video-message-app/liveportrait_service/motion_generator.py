"""
Motion Generator Model for JoyVASA

Diffusion Transformer (DiT) architecture for generating motion sequences from audio features.
Based on the JoyVASA paper: https://arxiv.org/abs/2411.09209
"""
import math
import logging
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class SinusoidalPositionEmbedding(nn.Module):
    """Sinusoidal position embeddings for timestep encoding"""

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, timesteps: torch.Tensor) -> torch.Tensor:
        """
        Args:
            timesteps: (B,) tensor of timesteps in [0, 1]

        Returns:
            Embeddings of shape (B, dim)
        """
        device = timesteps.device
        half_dim = self.dim // 2
        embeddings = math.log(10000) / (half_dim - 1)
        embeddings = torch.exp(torch.arange(half_dim, device=device) * -embeddings)
        embeddings = timesteps[:, None] * embeddings[None, :]
        embeddings = torch.cat([torch.sin(embeddings), torch.cos(embeddings)], dim=-1)
        return embeddings


class FeedForward(nn.Module):
    """Feed-forward network with GELU activation"""

    def __init__(self, dim: int, hidden_dim: int, dropout: float = 0.0):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.Dropout(dropout)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CrossAttention(nn.Module):
    """Cross-attention layer for audio-motion interaction"""

    def __init__(self, dim: int, context_dim: int, num_heads: int = 8, dropout: float = 0.0):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5

        self.q_proj = nn.Linear(dim, dim)
        self.k_proj = nn.Linear(context_dim, dim)
        self.v_proj = nn.Linear(context_dim, dim)
        self.out_proj = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Query tensor (B, T, D)
            context: Context tensor (B, T, C)

        Returns:
            Attended tensor (B, T, D)
        """
        B, T, D = x.shape

        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(context).view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(context).view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)

        attn = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, D)
        return self.out_proj(out)


class SelfAttention(nn.Module):
    """Self-attention layer for temporal modeling"""

    def __init__(self, dim: int, num_heads: int = 8, dropout: float = 0.0):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5

        self.qkv_proj = nn.Linear(dim, dim * 3)
        self.out_proj = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor (B, T, D)

        Returns:
            Output tensor (B, T, D)
        """
        B, T, D = x.shape

        qkv = self.qkv_proj(x).view(B, T, 3, self.num_heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]

        attn = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, D)
        return self.out_proj(out)


class TransformerBlock(nn.Module):
    """Transformer block with self-attention, cross-attention, and feed-forward"""

    def __init__(
        self,
        dim: int,
        context_dim: int,
        num_heads: int = 8,
        ff_mult: int = 4,
        dropout: float = 0.0
    ):
        super().__init__()

        # Self-attention
        self.norm1 = nn.LayerNorm(dim)
        self.self_attn = SelfAttention(dim, num_heads, dropout)

        # Cross-attention to audio features
        self.norm2 = nn.LayerNorm(dim)
        self.cross_attn = CrossAttention(dim, context_dim, num_heads, dropout)

        # Feed-forward
        self.norm3 = nn.LayerNorm(dim)
        self.ff = FeedForward(dim, dim * ff_mult, dropout)

        # Timestep modulation
        self.time_mlp = nn.Sequential(
            nn.SiLU(),
            nn.Linear(dim, dim * 2)
        )

    def forward(
        self,
        x: torch.Tensor,
        context: torch.Tensor,
        time_emb: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            x: Motion tensor (B, T, D)
            context: Audio features (B, T, C)
            time_emb: Time embeddings (B, D)

        Returns:
            Updated motion tensor (B, T, D)
        """
        # Timestep modulation
        scale, shift = self.time_mlp(time_emb).chunk(2, dim=-1)
        scale = scale.unsqueeze(1)
        shift = shift.unsqueeze(1)

        # Self-attention with time modulation
        x = x + self.self_attn(self.norm1(x) * (1 + scale) + shift)

        # Cross-attention to audio
        x = x + self.cross_attn(self.norm2(x), context)

        # Feed-forward
        x = x + self.ff(self.norm3(x))

        return x


class MotionDiffusionTransformer(nn.Module):
    """
    Diffusion Transformer for motion generation from audio

    Architecture:
    - Input: Noisy motion sequence + audio features + timestep
    - Output: Predicted noise
    """

    def __init__(
        self,
        audio_dim: int = 768,       # HuBERT feature dimension
        motion_dim: int = 66,        # LivePortrait motion coefficients
        hidden_dim: int = 512,       # Transformer hidden dimension
        num_layers: int = 6,         # Number of transformer blocks
        num_heads: int = 8,          # Number of attention heads
        dropout: float = 0.1
    ):
        super().__init__()

        self.motion_dim = motion_dim
        self.hidden_dim = hidden_dim

        # Input projections
        self.motion_proj = nn.Linear(motion_dim, hidden_dim)
        self.audio_proj = nn.Linear(audio_dim, hidden_dim)

        # Timestep embedding
        self.time_embed = nn.Sequential(
            SinusoidalPositionEmbedding(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim)
        )

        # Positional encoding for sequences
        self.pos_embed = nn.Parameter(torch.randn(1, 1024, hidden_dim) * 0.02)

        # Transformer blocks
        self.blocks = nn.ModuleList([
            TransformerBlock(
                dim=hidden_dim,
                context_dim=hidden_dim,
                num_heads=num_heads,
                ff_mult=4,
                dropout=dropout
            )
            for _ in range(num_layers)
        ])

        # Output projection
        self.norm_out = nn.LayerNorm(hidden_dim)
        self.out_proj = nn.Linear(hidden_dim, motion_dim)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize model weights"""
        def _basic_init(module):
            if isinstance(module, nn.Linear):
                torch.nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0)

        self.apply(_basic_init)

        # Zero-initialize output projection for residual connection
        nn.init.zeros_(self.out_proj.weight)
        nn.init.zeros_(self.out_proj.bias)

    def forward(
        self,
        motion: torch.Tensor,
        audio_features: torch.Tensor,
        timesteps: torch.Tensor
    ) -> torch.Tensor:
        """
        Forward pass for noise prediction

        Args:
            motion: Noisy motion sequence (B, T, motion_dim)
            audio_features: Audio features (B, T, audio_dim)
            timesteps: Diffusion timesteps (B,) in [0, 1]

        Returns:
            Predicted noise (B, T, motion_dim)
        """
        B, T, _ = motion.shape

        # Project inputs
        h = self.motion_proj(motion)
        context = self.audio_proj(audio_features)

        # Add positional encoding
        h = h + self.pos_embed[:, :T, :]
        context = context + self.pos_embed[:, :T, :]

        # Time embedding
        time_emb = self.time_embed(timesteps)

        # Transformer blocks
        for block in self.blocks:
            h = block(h, context, time_emb)

        # Output projection
        h = self.norm_out(h)
        noise_pred = self.out_proj(h)

        return noise_pred


class MotionEncoder(nn.Module):
    """
    Encoder to extract motion from source image
    Used to get initial motion state from reference frame
    """

    def __init__(self, motion_dim: int = 66):
        super().__init__()
        self.motion_dim = motion_dim
        # This would typically be loaded from LivePortrait's motion extractor
        # For now, placeholder

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        Extract motion coefficients from image

        Args:
            image: Input image (B, 3, H, W)

        Returns:
            Motion coefficients (B, motion_dim)
        """
        # Placeholder - actual implementation uses LivePortrait's motion extractor
        raise NotImplementedError("Use LivePortrait's motion extractor instead")


class MotionDecoder(nn.Module):
    """
    Decoder to convert motion coefficients to keypoints
    """

    def __init__(self, motion_dim: int = 66, num_kp: int = 21):
        super().__init__()
        self.motion_dim = motion_dim
        self.num_kp = num_kp
        # Placeholder for converting motion to keypoints

    def forward(self, motion: torch.Tensor) -> torch.Tensor:
        """
        Convert motion coefficients to 3D keypoints

        Args:
            motion: Motion coefficients (B, T, motion_dim)

        Returns:
            3D keypoints (B, T, num_kp, 3)
        """
        # Placeholder - actual implementation uses LivePortrait's keypoint format
        raise NotImplementedError("Use LivePortrait's motion processing instead")
