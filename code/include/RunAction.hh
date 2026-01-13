

#ifndef RunAction_h
#define RunAction_h 1
#include "DetectorConstruction.hh"
#include "G4UserRunAction.hh"
#include "globals.hh"

#include <fstream>

using namespace std;
class G4Run;

class RunAction : public G4UserRunAction
{
  public:
    RunAction();
    ~RunAction() override = default;

  public:
    void BeginOfRunAction(const G4Run*) override;
    void   EndOfRunAction(const G4Run*) override;

	G4double Run_EdepInCrystal[128];    // 探测器阵列数量
	G4double Run_EdepInCrystal2[128];    // 探测器阵列数量
};

#endif

