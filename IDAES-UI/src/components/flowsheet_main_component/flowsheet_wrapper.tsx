import { useContext, useEffect } from "react";
import {AppContext} from "../../context/appMainContext";

import { PanelGroup, Panel, PanelResizeHandle} from "react-resizable-panels";
import FlowsheetHeader from "./flowsheet_component/flowsheet_header/flowsheet_header_component";
import Flowsheet from "./flowsheet_component/flowsheet_component";
import FlowsheetVariablesHeader from "./flowsheet_variables/flowsheet_variables_header/flowsheet_variables_header";
import Flowsheet_variable from "./flowsheet_variables/flowsheet_variable_component";
import StreamTable from "./stream_table_component/stream_table";

export default function FlowsheetWrapper(){
  const {panelState} = useContext(AppContext);
  const isFvShow:boolean = panelState.fv.show;
  const isVariablesShow:boolean = panelState.variables.show;
  const isStreamTableShow = panelState.streamTable.show;

  useEffect(()=>{
    
  },[])

  return(
    <>
      <PanelGroup direction="vertical">
        <Panel maxSize={100} defaultSize={70}>
          <PanelGroup direction="horizontal">
            {
              isFvShow && 
              <Panel defaultSize={70} minSize={0}>
                <FlowsheetHeader />
                <Flowsheet />
              </Panel>
            }

            <PanelResizeHandle className="panelResizeHandle panelResizeHandle_vertical"/>
            
            {
              isVariablesShow && 
              <Panel defaultSize={30} minSize={0}>
                <FlowsheetVariablesHeader />
                <Flowsheet_variable />
              </Panel>
            }
          </PanelGroup>
        </Panel>
            
        <PanelResizeHandle className="panelResizeHandle panelResizeHandle_horizontal"/>

        {
          isStreamTableShow &&
          <Panel maxSize={100} defaultSize={30}>
            <StreamTable />
          </Panel>
        }
        
      </PanelGroup>
    </>
  )
}