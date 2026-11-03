import { useState } from "react";

export default function DataTable({ columns, rows, onRowClick, emptyText }) {
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState("asc");
  
  function handleHeaderClick(columnKey) {
    if (sortColumn === columnKey) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else {
        setSortColumn(null);
        setSortDirection("asc");
      }
    } else {
      setSortColumn(columnKey);
      setSortDirection("asc");
    }
  }
  
  function getSortedRows() {
    if (!sortColumn) {
      return rows;
    }
    
    const sorted = [...rows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      
      const aNum = Number(aVal);
      const bNum = Number(bVal);
      
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return sortDirection === "asc" ? aNum - bNum : bNum - aNum;
      }
      
      const aStr = String(aVal);
      const bStr = String(bVal);
      const comparison = aStr.localeCompare(bStr);
      
      return sortDirection === "asc" ? comparison : -comparison;
    });
    
    return sorted;
  }
  
  const sortedRows = getSortedRows();
  
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-2 border-secondary bg-white">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={() => handleHeaderClick(col.key)}
                className="bg-secondary text-white font-mono text-xs uppercase tracking-wider text-left px-3 py-3 cursor-pointer"
              >
                {col.label}
                {sortColumn === col.key && (
                  <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="border-t-2 border-secondary px-3 py-3 font-body text-sm text-black text-center">
                {emptyText}
              </td>
            </tr>
          ) : (
            sortedRows.map((row, index) => (
              <tr
                key={index}
                onClick={() => onRowClick && onRowClick(row)}
                className={onRowClick ? "cursor-pointer hover:bg-primary" : ""}
              >
                {columns.map((col) => (
                  <td key={col.key} className="border-t-2 border-secondary px-3 py-3 font-body text-sm text-black">
                    {col.render ? col.render(row[col.key], row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
