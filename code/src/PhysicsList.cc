

#include "PhysicsList.hh"

#include "G4EmStandardPhysics.hh"
#include "G4EmStandardPhysics_option4.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4EmPenelopePhysics.hh"
#include "G4ParticleTypes.hh"

#include "G4SystemOfUnits.hh"
#include "G4DecayPhysics.hh"
#include "G4RadioactiveDecayPhysics.hh"

// particles
#include "G4BosonConstructor.hh"
#include "G4LeptonConstructor.hh"
#include "G4MesonConstructor.hh"
#include "G4BosonConstructor.hh"
#include "G4BaryonConstructor.hh"
#include "G4IonConstructor.hh"
#include "G4ShortLivedConstructor.hh"

PhysicsList::PhysicsList() : G4VModularPhysicsList()
{

	// Decay
	RegisterPhysics(new G4DecayPhysics());

	// Radioactive decay
	RegisterPhysics(new G4RadioactiveDecayPhysics());   //添加放射性衰变过程

	// EM Physics 以下四选一即可
	//RegisterPhysics(new G4EmStandardPhysics());
	RegisterPhysics(new G4EmStandardPhysics_option4());
	//RegisterPhysics(new G4EmLivermorePhysics());
	//RegisterPhysics(new G4EmPenelopePhysics());	

   SetDefaultCutValue(0.03*mm); 
}


PhysicsList::~PhysicsList() {}

void PhysicsList::SetCuts(){
	
	SetCutsWithDefault();
}

void PhysicsList::ConstructParticle()
{
  G4BosonConstructor  pBosonConstructor;
  pBosonConstructor.ConstructParticle();

  G4LeptonConstructor pLeptonConstructor;
  pLeptonConstructor.ConstructParticle();

  G4MesonConstructor pMesonConstructor;
  pMesonConstructor.ConstructParticle();

  G4BaryonConstructor pBaryonConstructor;
  pBaryonConstructor.ConstructParticle();

  G4IonConstructor pIonConstructor;
  pIonConstructor.ConstructParticle();

  G4ShortLivedConstructor pShortLivedConstructor;
  pShortLivedConstructor.ConstructParticle();  
}
