#ifndef PrimaryGeneratorAction_h
#define PrimaryGeneratorAction_h 1

#include "G4VUserPrimaryGeneratorAction.hh"
#include "globals.hh"
#include "G4ThreeVector.hh"
#include <vector>

class G4GeneralParticleSource;
class G4ParticleGun;
class G4Event;


class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction
{
public:
    PrimaryGeneratorAction();
    ~PrimaryGeneratorAction();

    void GeneratePrimaries(G4Event* anEvent);

private:
    G4ParticleGun* fParticleGun;
    // --- 能谱采样新增部分 ---
    void LoadSpectrum(G4String filename); // 加载 txt 文件
    G4double SampleEnergy();              // 执行连续采样
    
    std::vector<G4double> fEnergies;      // 存储能量点 (keV)
    std::vector<G4double> fCDF;           // 存储累积概率分布
    
    // 预计算的角度范围和常量（避免每次事件都计算）
    static const G4double fPhiMin;
    static const G4double fPhiMax;
    static const G4double fThetaMin;
    static const G4double fThetaMax;
    static const G4double fPhiRange;
    static const G4double fThetaRange;
    static const G4ThreeVector fSourcePosition;
};


// class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction
// {
// public:
//     PrimaryGeneratorAction();
//     ~PrimaryGeneratorAction();
	
// public:
//     void GeneratePrimaries(G4Event* anEvent);
	
// 	// method to access particle gun
//     G4GeneralParticleSource* GetParticleGun() const { return particleGun; }
// private:
//     G4GeneralParticleSource* particleGun;
	
// };

#endif
