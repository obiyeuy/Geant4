#include "PrimaryGeneratorAction.hh"
#include "Randomize.hh"
#include "G4Event.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4ParticleDefinition.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "globals.hh"
#include "G4ios.hh"
#include "fstream"
#include "iomanip"
#include "G4GeneralParticleSource.hh" 
using namespace std;	 

PrimaryGeneratorAction::PrimaryGeneratorAction()
{
    G4int n_particle = 1;
    fParticleGun = new G4ParticleGun(n_particle);

    // 定义粒子类型 x射线
    G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
    G4String particleName;
    G4ParticleDefinition* particle = particleTable->FindParticle(particleName = "gamma");
    fParticleGun->SetParticleDefinition(particle);

    // 设置粒子能量
    fParticleGun->SetParticleEnergy(160.0 * keV);
}

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
    delete fParticleGun;
}

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
    // 设置粒子发射位置
    fParticleGun->SetParticlePosition(G4ThreeVector(0*mm, 0*mm, -433.*mm));

    // 定义扇形束的角度范围
    G4double phiMin = -0.15 * deg;
    G4double phiMax = 0.15 * deg;
    G4double thetaMin = -6 * deg;
    G4double thetaMax = 6 * deg;

    // 随机生成角度
    G4double phi = G4UniformRand() * (phiMax - phiMin) + phiMin;
    G4double theta = G4UniformRand() * (thetaMax - thetaMin) + thetaMin;

    // 将角度转换为方向向量
    G4double sinTheta = std::sin(theta);
    G4double cosTheta = std::cos(theta);
    G4double sinPhi = std::sin(phi);
    G4double cosPhi = std::cos(phi);

	G4ThreeVector direction(sinTheta , cosTheta * sinPhi,  cosTheta * cosPhi);

    // 设置粒子发射方向
    fParticleGun->SetParticleMomentumDirection(direction);

    // 产生初级粒子
    fParticleGun->GeneratePrimaryVertex(anEvent);
}    