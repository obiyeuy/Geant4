#ifndef PrimaryGeneratorAction_h
#define PrimaryGeneratorAction_h 1

#include "G4VUserPrimaryGeneratorAction.hh"
#include "globals.hh"
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
