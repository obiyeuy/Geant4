

#ifndef RunAction_h
#define RunAction_h 1
#include "DetectorConstruction.hh"
#include "G4UserRunAction.hh"
#include "globals.hh"

#include <fstream>
#include <mutex>

using namespace std;
class G4Run;

class RunAction : public G4UserRunAction
{
  public:
    RunAction();
    RunAction(const RunAction&) = delete;  // 禁止拷贝构造
    RunAction& operator=(const RunAction&) = delete;  // 禁止赋值
    ~RunAction() override = default;

  public:
    void BeginOfRunAction(const G4Run*) override;
    void   EndOfRunAction(const G4Run*) override;
    
    // 线程安全的能量沉积累加方法
    void AddEdepInCrystal(G4int index, G4double edep);
    void AddEdepInCrystal2(G4int index, G4double edep);

	G4double Run_EdepInCrystal[128];    // 探测器阵列数量
	G4double Run_EdepInCrystal2[128];    // 探测器阵列数量
	
  private:
    // 互斥锁保护能量沉积累加操作
    static std::mutex fEdepMutex;
    static std::mutex fEdepMutex2;
};

#endif

