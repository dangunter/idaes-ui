import { createContext, useState, ReactNode, useEffect } from "react";
import axios from 'axios';

export const AppContext = createContext<any>({});

export function AppContextProvider({ children }: { children: ReactNode }){
  //App panel control
  const [panelState, setPanelState] = useState([
    {
      panelName : "Flowsheet",
      show : true
    },
    {
      panelName : "Variables",
      show : true
    },
    {
      panelName : "Stream Table",
      show : true
    },
    {
      panelName : "Report",
      show : false
    },
    {
      panelName : "Diagnostics",
      show : true
    },
  ]);
  //App panel control end

  //demo flowsheet state
  const [flowsheetState, setFlowsheetState] = useState(null);

  async function loadDemoFlowsheet(){
    try {
      const res = await axios.get('/data/demo_flowsheet.json');
      const JSON = res.data
      setFlowsheetState(JSON)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(()=>{
    loadDemoFlowsheet()
  },[])

  return(
    <AppContext.Provider value={{
      //view btn
      panelState,
      setPanelState,
      flowsheetState,
    }}>
      {children}
    </AppContext.Provider>
  )
}