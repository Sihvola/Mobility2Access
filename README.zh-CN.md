# Mobility2Access：基于出行行为的空间可达性分析

[English README](README.md)

这是一个 Python 科研原型，实现基于高斯距离衰减的两步移动搜索法（Gaussian 2SFCA）和人口加权的 Gini / Lorenz 公平性分析。研究特色是**依据观测到的公园访问出行行为，按年龄和公园规模设置服务距离阈值**。

**论文**：Guo, S., Song, C., Pei, T., et al. (2019). *Accessibility to urban parks for elderly residents: Perspectives from mobile phone data*. Landscape and Urban Planning, 191, 103642. DOI: https://doi.org/10.1016/j.landurbplan.2019.103642

## 北京老年人经验阈值

- 小型公园（2–20 ha）：5.3021 km
- 中型公园（20–100 ha）：6.9710 km
- 大型公园（>100 ha）：7.8076 km

这是特定样本的历史经验估计，不应当视为普适阈值。代码将20 ha划入中型，默认北京预设仅适用于面积大于2 ha的公园。

## 安装与运行

```bash
pip install -e ".[test]"
pytest -q
python examples/run_demo.py
```

空间文件支持需要安装 `pip install -e ".[gis,test]"`。

## 数据

1. 研究单元（`unit_id`、目标人口数量；可带 GeoDataFrame 几何）。
2. 公园（`park_id`、`park_area_ha`，可附带 `threshold_km`）。
3. 单元到公园的路网距离长表（`unit_id`、`park_id`、`network_distance_km`）。
4. 距离阈值：北京经验值、统一数值、分规模字典或逐公园字段。

既可以使用网格，也可以使用街道、社区，但人口数据与路网距离必须采用相同空间单元。**当前版本并不能根据边界自动计算路网距离**。

## 使用示例

```python
import pandas as pd
from mobility2access import calculate_accessibility

units = pd.read_csv("data/synthetic/grids.csv")
parks = pd.read_csv("data/synthetic/parks.csv")
distances = pd.read_csv("data/synthetic/grid_road_distances.csv")
result = calculate_accessibility(
    units, parks, distances,
    population_column="elderly_population",
    thresholds="beijing2019_elderly",
)
print(result.units)
print(result.gini)
```

可以使用 `calibrate_thresholds(visits)` 对已经提取出的公园访问记录按年龄和公园规模统计出行网络距离75%分位数。该接口不处理原始手机信令轨迹。

## 适用范围

这是一套论文核心方法的 Python 重构，**尚未通过原始数据证明完全复现原论文的所有结果**。附带数据完全为合成示例。模型使用传统 Gaussian 2SFCA 与 Gini，方法特色在于行为驱动的阈值标定。当前项目尚未确定软件开源许可证。

详细参见 [方法说明](docs/METHOD.md) 和 [数据格式](docs/DATA_FORMAT.md)。
