

#ifndef EventAction_h
#define EventAction_h 1

#include <fstream>
#include "DetectorConstruction.hh"
#include "G4UserEventAction.hh"
#include "globals.hh"

using namespace std;

class DetectorConstruction;
class G4Event;
class RunAction;

class EventAction : public G4UserEventAction
{
  public:
    EventAction(RunAction*);
    ~EventAction();

  public:
    void BeginOfEventAction(const G4Event*);
    void EndOfEventAction(const G4Event*);


    //G4double     totEnergyDepCathod;
    G4double  TEdep;
    G4int TNum;
    G4int MyeventID;
    G4double  k_primary;
    
    G4double EdepInCrystal[128];       // 探测器阵列数量
    G4double EdepInCrystal2[128];       // 探测器阵列数量
  private:
    RunAction*       runAction;
    G4int fDetNum;                      // 缓存的探测器像素数量
};

#endif
