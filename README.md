# 蜀洮的越狱源

个人自用的 iOS 越狱插件源（rootless arm64，iOS 15.0+）。

## 添加源

Sileo → 软件源 → 右上角 **+** → 输入：

```
https://shu-tao.github.io/shutao-repo/
```

## 已有插件

| 插件 | 标识 | 说明 |
| --- | --- | --- |
| 插件管理 | `com.shutao.pluginmanager` | 独立 App 形式的越狱插件管理器，逐项开关注入插件 |

## 收录新插件

```powershell
.\scripts\add-deb.ps1 -Path 'D:\DeepSeek Harness\projects\<项目>\Release\xxx.deb'
git add -A; git commit -m "add xxx"; git push
```

Sileo 刷新源即可看到。

## 结构

```
shutao-repo/
├── Packages            索引（另有 .gz/.bz2/.xz）
├── Release             源元信息
├── debs/               所有 deb 实际存放
│   └── old/            手动归档的旧版
└── scripts/
    ├── add-deb.ps1     收录单个 deb
    └── rebuild.py      重扫 debs/ 重建索引
```

## 索引规则

同一个包有多个版本时，索引只收录版本号最高的那个。旧版 deb 仍留在 `debs/` 里但不进索引。

## 免责

个人自用源，插件不保证稳定性，安装前请自行确认兼容性。
