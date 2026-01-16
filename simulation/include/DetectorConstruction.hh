
#ifndef DetectorConstruction_h
#define DetectorConstruction_h 1

#include "G4VUserDetectorConstruction.hh"
#include "G4RotationMatrix.hh"
class DetectorMessenger;
class G4VPhysicalVolume;

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

  private:
    G4double ObjShift;
    G4bool fEnableObject;  // 是否启用物体（用于生成空白灰度图）
    DetectorMessenger*  fMessenger;   // detector messenger  
    G4VPhysicalVolume* fPhysiObject; // 定义一个成员变量指针
};

#endif

