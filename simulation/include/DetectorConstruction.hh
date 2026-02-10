
#ifndef DetectorConstruction_h
#define DetectorConstruction_h 1

#include "G4VUserDetectorConstruction.hh"
#include "G4RotationMatrix.hh"
#include "G4GDMLParser.hh"
class DetectorMessenger;
class G4VPhysicalVolume;
class G4LogicalVolume;

class DetectorConstruction : public G4VUserDetectorConstruction
{
  public:
    DetectorConstruction();
    ~DetectorConstruction();

  public:
     G4VPhysicalVolume* Construct();
     const G4int DetPixNum = 128;    // 阵列数量
    G4RotationMatrix* fArmRotation;
    void SetObjShiftDistance (G4double );
    G4double GetObjShiftDistance() const { return ObjShift; }  // 获取ObjShift值
    void SetEnableObject (G4bool enable);  // 设置是否启用物体
    G4bool GetEnableObject() const { return fEnableObject; }  // 获取是否启用物体
    void LoadOreGDML(G4String filename);  // 动态加载矿石 GDML 文件
    void SetMaterialSlabMaterial(G4String materialName);  // 设置材料板材料
    void SetMaterialSlabThickness(G4double thickness);  // 设置材料板厚度
    G4double GetMaterialSlabThickness() const { return fMaterialSlabThickness; }  // 获取材料板厚度

  private:
    G4double ObjShift;
    G4bool fEnableObject;  // 是否启用物体（用于生成空白灰度图）
    DetectorMessenger*  fMessenger;   // detector messenger  
    G4VPhysicalVolume* fPhysiObject; // 定义一个成员变量指针
    G4LogicalVolume* fLogicOre;  // 矿石逻辑体积指针（用于动态替换）
    G4GDMLParser fParser;  // GDML 解析器
    G4Material* fMaterialSlabMaterial;  // 材料板材料
    G4double fMaterialSlabThickness;  // 材料板厚度
    G4VPhysicalVolume* fPhysiMaterialSlab;  // 材料板物理体积指针
    G4LogicalVolume* fLogicMaterialSlab;  // 材料板逻辑体积指针
};

#endif

