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
    // fParticleGun->SetParticleEnergy(160.0 * keV);
    // 加载生成的能谱文件 (确保 spectrum.txt 在 build 运行目录下)
    LoadSpectrum("src/spectrum.txt");
}

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
    delete fParticleGun;
}

// void PrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
// {
//     // 设置粒子发射位置
//     fParticleGun->SetParticlePosition(G4ThreeVector(0*mm, 0*mm, -433.*mm));

//     // 定义扇形束的角度范围
//     G4double phiMin = -0.15 * deg;
//     G4double phiMax = 0.15 * deg;
//     G4double thetaMin = -6 * deg;
//     G4double thetaMax = 6 * deg;

//     // 随机生成角度
//     G4double phi = G4UniformRand() * (phiMax - phiMin) + phiMin;
//     G4double theta = G4UniformRand() * (thetaMax - thetaMin) + thetaMin;

//     // 将角度转换为方向向量
//     G4double sinTheta = std::sin(theta);
//     G4double cosTheta = std::cos(theta);
//     G4double sinPhi = std::sin(phi);
//     G4double cosPhi = std::cos(phi);

// 	G4ThreeVector direction(sinTheta , cosTheta * sinPhi,  cosTheta * cosPhi);

//     // 设置粒子发射方向
//     fParticleGun->SetParticleMomentumDirection(direction);

//     // 产生初级粒子
//     fParticleGun->GeneratePrimaryVertex(anEvent);
// }    

void PrimaryGeneratorAction::LoadSpectrum(G4String filename)
{
    std::ifstream file(filename);
    if (!file.is_open()) {
        G4Exception("PrimaryGeneratorAction", "FileNotOpen", FatalException, "Could not find spectrum.txt!");
    }

    G4double energy, weight;
    const G4double energyThreshold = 20.0; // keV，截断阈值
    G4double filteredTotalWeight = 0;
    G4int originalCount = 0;
    std::vector<std::pair<G4double, G4double>> filteredData;

    // 读取并截断：只保留能量 >= 阈值的点
    while (file >> energy >> weight) {
        originalCount++;
        if (energy >= energyThreshold) {
            filteredData.push_back({energy, weight});
            filteredTotalWeight += weight;
        }
    }
    file.close();

    // 检查截断后是否还有数据
    if (filteredData.empty()) {
        G4Exception("PrimaryGeneratorAction", "EmptySpectrum", FatalException, 
                    "All spectrum data filtered out! Check energy threshold.");
    }

    // 构建累积分布函数 (CDF)，使用截断后的数据并重新归一化
    G4double cumulative = 0;
    for (auto const& data : filteredData) {
        cumulative += data.second / filteredTotalWeight;
        fEnergies.push_back(data.first * keV);
        fCDF.push_back(cumulative);
    }
    
    G4cout << "##### Spectrum loaded: " << filteredData.size() << " / " << originalCount 
           << " points (energy >= " << energyThreshold << " keV)" << G4endl;
    G4cout << "##### Energy range: " << filteredData.front().first << " - " 
           << filteredData.back().first << " keV" << G4endl;
}

G4double PrimaryGeneratorAction::SampleEnergy()
{
    G4double r = G4UniformRand();
    
    // 边界检查：防止随机数超出范围
    if (r <= 0.0) return fEnergies[0];
    if (r >= 1.0) return fEnergies.back();
    
    // 使用二分查找定位随机数所在的区间
    auto it = std::lower_bound(fCDF.begin(), fCDF.end(), r);
    int idx = std::distance(fCDF.begin(), it);

    // 处理边界情况
    if (idx == 0) return fEnergies[0];
    if (it == fCDF.end()) return fEnergies.back();

    // --- 线性插值逻辑：实现绝对连续采样 ---
    G4double e1 = fEnergies[idx-1];
    G4double e2 = fEnergies[idx];
    G4double p1 = fCDF[idx-1];
    G4double p2 = fCDF[idx];

    // 防止除零错误（理论上不应该发生，但安全起见）
    if (p2 == p1) return e1;

    // 根据随机数在概率区间的位置，线性映射到能量区间
    return e1 + (e2 - e1) * (r - p1) / (p2 - p1);
}

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
    // 1. 采样能谱能量并设置
    fParticleGun->SetParticleEnergy(SampleEnergy());

    // 2. 设置发射位置
    fParticleGun->SetParticlePosition(G4ThreeVector(0*mm, 0*mm, -433.*mm));

    // 3. 设置扇形束角度 (已优化的精确范围)
    G4double phiMin = -0.15 * deg;
    G4double phiMax = 0.15 * deg;
    G4double thetaMin = -6.0 * deg;
    G4double thetaMax = 6.0 * deg;

    G4double phi = G4UniformRand() * (phiMax - phiMin) + phiMin;
    G4double theta = G4UniformRand() * (thetaMax - thetaMin) + thetaMin;

    G4double sinTheta = std::sin(theta);
    G4double cosTheta = std::cos(theta);
    G4double sinPhi = std::sin(phi);
    G4double cosPhi = std::cos(phi);

    // 4. 计算并设置方向
    G4ThreeVector direction(sinTheta, cosTheta * sinPhi, cosTheta * cosPhi);
    fParticleGun->SetParticleMomentumDirection(direction);

    fParticleGun->GeneratePrimaryVertex(anEvent);
}