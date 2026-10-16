using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;

using Microsoft.Win32;

namespace Tree.View {
    public partial class MainWindow : Window {

        public string TreeFile { get; set; }
        public string TreeDir { get; set; }
        public string TreeName { get; set; }
        public string TreeExt { get; set; }
        public string LogDir { get; set; }
        public string LogFile { get; set; }
        internal string DGMLTreeFile;
        internal string DGMLDir;
        internal string DGMLTreeName;

        public bool OpenDiTree() {
            bool openOK;
            OpenFileDialog openFile = new OpenFileDialog() { Filter = "csx files (*.csx)|*.csx|All files (*.*)|*.*" };
            if (openOK = openFile.ShowDialog() == true) {
                TreeFile = openFile.FileName;
                TreeDir = Path.GetDirectoryName(TreeFile);
                TreeName = Path.GetFileNameWithoutExtension(TreeFile);
                TreeExt = Path.GetExtension(TreeFile);
                LogDir = Directory.CreateDirectory(TreeDir + "\\Log\\").FullName;
                LogFile = LogDir + TreeName + ".log";
            }
            return (openOK);
        }

        public void ReadDiGraph() {
            var graph = new StreamReader(TreeFile);
            string line;
            int numLines = 0;
            while ((line = graph.ReadLine()) != null) {
                numLines++;
                if (line == "") continue;
                if (line.Substring(0, 1) == "#") { continue; }
                if (line.Substring(0, 2) == "--") { continue; }
                if (line.Substring(0, 2) == "**") { continue; }
                if (line.Substring(0, 2) == "@@") { break; }
                var edgeDef = line.Split(':');
                var uDef = edgeDef[0].Trim();
                ;
                var succList = edgeDef[1].Split(';');
                if (edgeDef[1] == "") { continue; }
                var succs = succList.GetUpperBound(0);
                for (int i = 0; i <= succs; i++) {
                    var vDef = succList[i].Trim();
                    if (vDef == "") continue;
                    try {
                        T.Insert(uDef, vDef);
                    } catch (Exception e) when (e is ArgumentException || e is KeyNotFoundException) {
                        MessageBox.Show($"Line {numLines}: ({uDef}, {vDef}) skipped.\n{e.Message}", "DTree", MessageBoxButton.OK, MessageBoxImage.Warning);
                    }
                }
            }
            graph.Close();
        }
    }
}