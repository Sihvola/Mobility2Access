# Mobility2Access：Python 复现与扩展

论文来源：Guo et al. (2019), *Accessibility to urban parks for elderly residents: Perspectives from mobile phone data*, Landscape and Urban Planning 191, 103642. https://doi.org/10.1016/j.landurbplan.2019.103642

本项目是**可运行的论文核心算法 Python 重构**，不是原始北京数据的完整数值复现。核心理念是：利用真实居民访问公园的出行距离（按年龄及公园规模分组）的 **75% 分位数**确定服务距离阈值，再使用 Gaussian 2SFCA 计算公园可达性，并分析公平性。Gaussian 2SFCA、基尼系数均为成熟方法；论文特色是基于实际出行行为确定差异化阈值。

## 最简输入

| 数据 | 必要字段 | 说明 |
|---|---|---|
| 研究单元和人口 | `unit_id`, `elderly_population`（列名可换） | 可以是网格或街道；可选 GeoJSON/GPKG 边界 |
| 公园 | `park_id`, `park_area_ha` | 单位：公顷，必须有公园供给面积 |
| 路网距离 | `unit_id`, `park_id`, `network_distance_km` | 与**当前研究单元**对应的公园最短路网距离（km） |
| 距离阈值 | 程序参数 `thresholds` | 论文北京经验值、统一值、自定义公园大小分组或每公园单独值 |

这里的“人口”是某研究单元内的**居住人口数（绝对人数）**，不是人口密度；分组计算时可以把 `population_column` 指向目标人群（例如老年人口）。输入网格则输出网格可达性；输入街道则输出街道可达性。**切换尺度时，路网距离也必须按新的单元重新准备**，不能只将网格结果简单平均当成街道计算值。

## 安装和运行

```bash
pip install -e ".[test]"
python examples/run_demo.py
pytest -q
```

命令行直接输出网格可达性：

```bash
mobility2access \
  --units data/synthetic/grids.csv \
  --parks data/synthetic/parks.csv \
  --distances data/synthetic/grid_road_distances.csv \
  --population-column elderly_population \
  --thresholds beijing2019_elderly \
  --output outputs/grid_access.csv
```

换成街道单元，只需将 `--units` 换为 `data/synthetic/streets.csv`，将 `--distances` 换为 `data/synthetic/street_road_distances.csv`，输出改为 `outputs/street_access.csv`。

空间文件：安装 `pip install -e ".[gis]"` 后，可将 `--units` 指向 `.geojson/.gpkg/.shp` 文件，将输出设为 `.geojson/.gpkg`；原有单元面要素和属性会一并保留。

## Python 示例

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
print(result.units)  # 每个研究单元新增 accessibility_m2_per_person
print(result.parks)  # 每个公园的服务阈值、加权需求量、供需比
print(result.gini)   # 按研究人群人口加权的基尼系数
```

其他阈值使用方式：

```python
thresholds=5.0  # 所有公园统一5公里
a = {"small":4.5, "medium":6.0, "large":8.0}
thresholds=a    # 按公园规模使用自定义距离阈值
thresholds="park_column"  # 从 parks 的 threshold_km 字段读取
```

### 原论文北京老年人（60岁及以上）经验参数

| 公园规模 | 面积（ha） | 阈值（km） |
|---|---|---:|
| 小型 | 2–20 | 5.3021 |
| 中型 | 20–100 | 6.9710 |
| 大型 | 大于100 | 7.8076 |

数据来自所附论文介绍文档图2。边界条件 20ha 被约定归为中型，`beijing2019_elderly` 模式限定公园面积必须 **>2 ha**。经验值用于当年北京老年人群体，其他地区/年龄段建议利用本地访问数据重新标定或输入自定义阈值。

### 计算公式

截断高斯权重：

```
w(d,D) = [exp(-0.5*(d/D)^2)-exp(-0.5)] / [1-exp(-0.5)]  (d<D)
w(d,D) = 0                                                   (d>=D)
R_j = S_j / sum_i(P_i * w_ij)
A_i = sum_j(R_j * w_ij)
```

`S_j` 用 m²，`P_i` 用居民人数，最终 `A_i` 单位 m²/人。每个公园可以有独立的 `D_j`，而且两步使用同一阈值。无法接触服务人群的公园，其供需比在软件中设置为零并给予标记，这属于明确的工程处理约定。

### 数据隐私和复现边界

- `data/synthetic/` 下的公园、街道、网格、路网距离、轨迹统计均为**虚构演示数据**，并非论文的北京实际数据。
- 已有距离阈值时**不需要**原始手机信令数据。`calibrate_thresholds()` 可利用提取后的公园访问路网距离表计算75%分位数，但**不直接提供**用户居住地识别、轨迹提取与公园访问识别模块。
- 当前实现是核心 Gaussian 2SFCA + 阈值管理 + 人口加权 Gini；不包含论文全部回归分析或与原数据结果的逐项检验。
- 使用不同人口与单元划分时，保证人口、路网距离及输出单元 ID 一致。公园实际入口及研究单元出发位置会影响距离结果。
- 项目源代码已采用 [BSD-3-Clause 开源许可证](LICENSE)，软件引用信息见 [CITATION.cff](CITATION.cff)。该许可证不改变2019年论文和第三方地图数据的版权及许可条件。

更完整的算法与不确定性说明：[docs/METHOD.md](docs/METHOD.md)，字段说明：[docs/DATA_FORMAT.md](docs/DATA_FORMAT.md)。

## 软件授权、学术引用和 OpenStreetMap 声明

**开源授权：** Mobility2Access 的原创软件代码采用 [BSD 3-Clause License](LICENSE)，版权声明为 © 2026 Sihui Guo and Mobility2Access contributors。许可证适用于软件代码，不自动覆盖论文全文、合作单位数据或者其他第三方数据。

**学术引用：** 仓库根目录的 [CITATION.cff](CITATION.cff) 用于引用 **Mobility2Access v0.2.0 软件**；如果采用论文提出的基于年龄与公园规模的出行距离阈值方法，也请同时引用原论文：

> Guo, S., Song, C., Pei, T., et al. (2019). *Accessibility to urban parks for elderly residents: Perspectives from mobile phone data*. Landscape and Urban Planning, 191, 103642. https://doi.org/10.1016/j.landurbplan.2019.103642

目前软件尚没有独立的 Zenodo DOI 或正式 GitHub Release，**原论文 DOI 不代表软件 DOI**。

**OSM 数据声明：** 使用在线路网功能时，数据来源于 **© OpenStreetMap contributors**，按 [Open Database License (ODbL)](https://www.openstreetmap.org/copyright) 授权。公开发布基于 OSM 的路网数据、地图和衍生成果时，应遵守 [OpenStreetMap 署名指南](https://osmfoundation.org/wiki/Attribution_Guidelines) 以及相关许可要求。软件采用 BSD-3-Clause，不意味着 OSM 数据自动采用 BSD。仓库自带示例空间数据为合成数据，不包含在线下载的 OSM 路网。

## v0.2：从空间数据自动计算路网距离

新增 `mobility2access.routing`，支持：

- 输入网格、街道等研究单元的 GeoJSON/GeoPackage（需要 `unit_id` 和人口字段）、公园边界及其 `park_id` / `park_area_ha`。
- 可选输入公园入口点（`park_id`，允许一园多入口）和研究单元实际人口中心点（`unit_id`）。
- 使用已有的投影步行路网（NetworkX/OSMnx GraphML），也可通过 OSMnx 在线获取 OpenStreetMap 的步行路网。
- 自动计算 **研究单元至公园入口的最短路网距离**，并按服务距离阈值筛选，直接调用原 Gaussian 2SFCA 模型。
- 生成与原模型完全兼容的三列 OD 距离表、可达性图层及公园诊断结果。

### 安装与离线演示

```bash
pip install -e ".[routing,test]"
python examples/run_routing_demo.py
pytest -q
```

### 真实 OpenStreetMap 步行路网（需要互联网）

```bash
pip install -e ".[osm,test]"
mobility2access-route \
  --units data/synthetic/grids.geojson \
  --parks data/synthetic/parks.geojson \
  --entrances data/synthetic/park_entrances.geojson \
  --download-osm \
  --population-column elderly_population \
  --thresholds beijing2019_elderly \
  --od-output outputs/od.csv \
  --output outputs/accessibility.geojson
```

输入中的公园位置均为**人工合成示例**，不是北京市真实公园位置。对于全北京市研究，建议提前下载或准备完整路网，运行时改为 `--graphml path/to/network.graphml`；对于大型公园，应优先提供真实出入口。公园边界自动选取的最近路网位置仅是入口近似，节点吸附距离也是直线连接的近似，不能等同于真实步行路径。

详见 [路网距离计算说明](docs/ROUTING.md)。