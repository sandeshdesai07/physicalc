// frontend/src/App.js
import React, {useState} from "react";

function App(){
  const [text,setText]=useState("");
  const [resp,setResp]=useState(null);

  async function ask(){
    const res = await fetch("http://localhost:8000/api/ask", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    setResp(data);
  }

  return (
    <div style={{padding:20}}>
      <h2>PhysiCalc — Quick Test</h2>
      <textarea rows={4} cols={60} value={text} onChange={e=>setText(e.target.value)} placeholder="Type a physics question..."/>
      <div>
        <button onClick={ask}>Ask</button>
      </div>
      {resp && (
        <pre style={{background:"#f0f0f0", padding:10}}>{JSON.stringify(resp,null,2)}</pre>
      )}
    </div>
  )
}

export default App;
