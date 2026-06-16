import { Column, Entity, PrimaryColumn } from 'typeorm';

@Entity('candles')
export class Candle {
  @PrimaryColumn('timestamptz')
  time: Date;

  @PrimaryColumn('text')
  instrument: string;

  @PrimaryColumn('text')
  granularity: string;

  @Column('decimal', { nullable: true })
  open: string | null;

  @Column('decimal', { nullable: true })
  high: string | null;

  @Column('decimal', { nullable: true })
  low: string | null;

  @Column('decimal', { nullable: true })
  close: string | null;

  @Column('int', { nullable: true })
  volume: number | null;
}
