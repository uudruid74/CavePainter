"""Backend-agnostic value types shared by the DrawingEngine port and its adapters."""
from dataclasses import dataclass
from typing import Literal

CanvasHandle = str
LayerHandle = str
BrushHandle = str
GradientStyle = Literal["linear", "radial"]
PathSegmentKind = Literal["moveto", "lineto", "conicto", "cubicto", "close"]


@dataclass(frozen=True)
class Color:
    r: float
    g: float
    b: float
    a: float = 1.0

    def as_list(self) -> list[float]:
        return [self.r, self.g, self.b]


@dataclass(frozen=True)
class PathSegment:
    """One command in a bezier path.
    Point counts by kind: moveto=(x,y), lineto=(x0,y0), conicto=(x0,y0,x1,y1),
    cubicto=(x0,y0,x1,y1,x2,y2), close=().
    """
    kind: PathSegmentKind
    points: tuple[float, ...] = ()


@dataclass(frozen=True)
class BrushSpec:
    name: str = "2. Hardness 100"
    size: float | None = None
    hardness: float | None = None
    aspect_ratio: float | None = None
    angle: float | None = None
    spacing: float | None = None
    force: float | None = None
