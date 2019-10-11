# RedQueen

### Download

##### > WGET method
```bash
wget http://modules.projectalice.ch/RedQueen \
-O ~/ProjectAlice/system/moduleInstallTickets/RedQueen.install
```

##### > Alice CLI method
```bash
./alice add module ProjectAlice RedQueen
```

### Desc
Red Queen is the official Project Alice personality module

- Version: 1.06
- Author: ProjectAlice
- Maintainers:
  - Psycho, Jierka, maxbachmann
- Alice minimum version: 0.12
- Conditions:
  - EN
  - FR
  - DE
- Requirements: N/A


### Configuration

`randomSpeeking`:
 - type: `bool`
 
`randomTalkMinDelay`:
 - type: `int`

`randomTalkMaxDelay`:
 - type: `int`
 
 `disableMoodTraits`:
 - type: `bool`


### Extra files

- redQueen.dist.json: Holds her mood statistics
- strings.json: some translation strings
