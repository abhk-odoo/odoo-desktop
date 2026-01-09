import { execSync } from "child_process";

function run(cmd) {
    console.log("▶▶▶", cmd);
    execSync(cmd, { stdio: "inherit" });
}

const arg = process.argv[2];

switch (arg) {
    case "clean":
        run(`npx rimraf build dist server/build server/main.spec server/__pycache__`);
        break;

    case "python-win":
        run(`cd server && pip install -r requirements.txt`);
        run(`cd server && pyinstaller --onefile --add-data "config/ddl_path.py;." --add-data "lib;lib" --collect-data=escpos --name main --distpath ../build/win-x64 main.py`);
        break;

    case "python-linux":
        run(`cd server && pip install -r requirements.txt`);
        run(`cd server && pyinstaller --onefile --add-data "config/ddl_path.py:." --add-data "lib:lib" --collect-data=escpos --name main --distpath ../build/linux-x64 main.py`);
        break;

    case "python-mac":
        run(`cd server && pip install -r requirements.txt`);
        run(`cd server && pyinstaller --onefile --add-data "config/ddl_path.py:." --add-data "lib:lib" --collect-data=escpos --name main --distpath ../build/mac-x64 main.py`);
        break;

    case "electron-win":
        run(`electron-builder --win nsis`);
        break;

    case "electron-linux":
        run(`electron-builder --linux deb`);
        break;
    
    case "electron-mac":
        run(`electron-builder --mac dmg`);
        break;

    case "win":
        run(`node build.js clean`);
        run(`node build.js python-win`);
        run(`node build.js electron-win`);
        break;

    case "linux":
        run(`node build.js clean`);
        run(`node build.js python-linux`);
        run(`node build.js electron-linux`);
        break;

    case "mac":
        run(`node build.js clean`);
        run(`node build.js python-mac`);
        run(`node build.js electron-mac`);
        break;

    default:
        break;
}
