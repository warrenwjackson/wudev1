function create_occupancy_graphic(occ, capacity){
  var s = "<j class='spacetaken'>";
  console.log('occ graphic');
  console.log(typeof occ);
  for (var i = 0; i < parseInt(occ); i++){
    console.log('looping occ');
    s = s.concat('&#9632;');
  }
  s = s.concat('</j><j class="spaceopen">');
  for (var i = 0; i < parseInt(capacity) - parseInt(occ); i++){
    s = s.concat('&#9633;');
  }
  s = s.concat('</j>');
  return s;
}
function create_dogga_graphic(has_dogs){
  if(has_dogs){return '<i class="fi-paw doggiestyle"></i>';}
  else {return '';}
}
function cast_to_string(maybe_string){
if (!(typeof maybe_string == 'string' || maybe_string instanceof String)){
return maybe_string.toString();
} else {
  return maybe_string;
}
}
function create_cell_simple(raw_cell, is_header){
var cell = cast_to_string(raw_cell);
console.log('create cell simple');
console.log(cell);
  if(is_header){return '<th>'.concat(cell,'</th>');}
  else {return '<td>'.concat(cell,'</td>');}
}
function create_cell(cell, is_header){
  var cell_str = '';
  console.log('create_cell called');
  console.log(cell);
  if(cell.cell_type == 'occupancy'){
    console.log(' it is an occ cell');
    cell_str = "<j data-reveal-id=\"addtoresv\" class='button resv' onclick=\"pop_resv_form(";
    cell_str = cell_str.concat("'", cell.ranch_id, "','", cell.ranch_display_name, "','", cell.blind_id, ', ', cell.date, "');\">");
    for(var i = 0; i < cell.occupancies.length; i++){
        console.log('looping occ');
        cell.occupancies[i];
        cell_str = cell_str.concat(create_occupancy_graphic(cell.occupancies[i]['occ'], cell.occupancies[i]['capacity']));
    }
    cell_str = cell_str.concat(create_dogga_graphic(cell.has_dogs));
    console.log(cell_str);
  } else if (cell.cell_type == 'raw'){
    cell_str = cast_to_string(cell.val);
    console.log(cell_str);
  }
  cell_str =  create_cell_simple(cell_str, is_header);
  console.log(cell_str);

  return cell_str;
}

function create_row(raw_rows, is_header){
  var row = '<tr>';
  console.log('create_row called');
  console.log(raw_rows);
  for (var i=0; i < raw_rows.length; i++){
    row = row.concat(create_cell(raw_rows[i], is_header));
  }
  row = row.concat('</tr>')
  return row;
}
function pop_ranch_table(data){
  console.log(typeof data);
  console.log(data);
  console.log(data.success);
  //$("#resvtable tr").remove();
  $("#resvtable").empty()
  var table = '';
  if(data.success){
    table = table.concat(create_row(data.header, true));
    for(var i = 0; i < data.table_data.length; i++){
      console.log('iterating row');
      table = table.concat(create_row(data.table_data[i], false));
    }
  } else {alert('Bad things!')}
  $('#resvtable').append(table);
}

function show_hide_people(show_rows){
    for(i=0;i<20;i++){
    if(i<show_rows){
      $('#person_'.concat(i)).show();  
    } else {
      $('#person_'.concat(i)).hide();  
      
    }
    
  }
}
function add_person_row(num_rows){
  console.log($('#id_show_rows').val());
  $('#person_'.concat( $('#id_show_rows').val())).show();
   $('#id_show_rows').val( parseInt($('#id_show_rows').val())+1);
   console.log($('#id_show_rows').val());
}
