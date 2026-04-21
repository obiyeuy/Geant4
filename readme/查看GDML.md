使用 ROOT 查看（最推荐，速度最快）
因为你的 ROOT 编译时开启了 gdml 和 opengl 支持，你可以直接用 ROOT 打开 GDML 文件，不需要写任何 C++ 代码。

打开终端。

输入 root 进入 ROOT 命令行环境。

依次输入以下两条命令（替换 你的文件名.gdml）：

C++

// 导入几何体
TGeoManager::Import("你的文件名.gdml");

// 绘制 (ogl 表示使用 OpenGL 交互式查看)
gGeoManager->GetTopVolume()->Draw("ogl");
效果： 会弹出一个图形窗口，你可以用鼠标旋转、缩放几何体。

优点：无需编译，即开即用。

注意：如果几何体非常复杂，ROOT 的渲染可能会比 Geant4 原生慢一点。