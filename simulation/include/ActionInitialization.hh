#ifndef ActionInitialization_h
#define ActionInitialization_h 1

#include "G4VUserActionInitialization.hh"

class RunAction;

class ActionInitialization : public G4VUserActionInitialization
{
  public:
    ActionInitialization(RunAction* runAction);
    ~ActionInitialization() override = default;

    void BuildForMaster() const override;
    void Build() const override;

  private:
    RunAction* fRunAction;
};

#endif



