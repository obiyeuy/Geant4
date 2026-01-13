
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

  private:
    G4double ObjShift;
    DetectorMessenger*  fMessenger;   // detector messenger  
};

#endif

