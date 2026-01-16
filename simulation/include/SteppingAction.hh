

#ifndef SteppingAction_h
#define SteppingAction_h 1

#include "G4UserSteppingAction.hh"
#include "globals.hh"

class EventAction;
class G4Material;
// class RunAction;

class SteppingAction : public G4UserSteppingAction
{
  public:
    SteppingAction(EventAction*);
    ~SteppingAction();

    void UserSteppingAction(const G4Step*);
    
  private:
    EventAction* eventAction;
    G4int fDetNum;              // 缓存的探测器像素数量
    const G4Material* fGOSMaterial;  // 缓存的GOS材料指针
    const G4Material* fGGAGMaterial; // 缓存的GGAG材料指针
};

#endif
